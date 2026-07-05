from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Producto, Categoria, Venta, DetalleVenta
from .forms import ProductoForm, CategoriaForm
from django.db.models import Q, ExpressionWrapper, BooleanField, F
import qrcode
import io
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json

@login_required
def lista_productos(request):
    query = request.GET.get('q', '')
    categoria_id = request.GET.get('categoria', '')

    productos = Producto.objects.annotate(
        en_peligro=ExpressionWrapper(
            Q(cantidad__lte=F('stock_minimo')),
            output_field=BooleanField()
        )
    ).order_by('-en_peligro', 'nombre')

    if query:
        productos = productos.filter(
            nombre__icontains=query
        ) | productos.filter(
            marca__icontains=query
        ) | productos.filter(
            codigo__icontains=query
        )

    if categoria_id:
        productos = productos.filter(categoria__id=categoria_id)

    categorias = Categoria.objects.all()
    return render(request, 'productos/lista.html', {
        'productos': productos,
        'categorias': categorias,
        'query': query,
        'categoria_id': categoria_id,
    })

@login_required
def agregar_producto(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST)
        if form.is_valid():
            form.save()
            if request.POST.get('desde_escaner'):
                return redirect('escanear')
            return redirect('lista_productos')
    else:
        form = ProductoForm()
    return render(request, 'productos/formulario.html', {'form': form, 'titulo': 'Agregar producto'})

@login_required
def editar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            form.save()
            return redirect('lista_productos')
    else:
        form = ProductoForm(instance=producto)
    return render(request, 'productos/formulario.html', {'form': form, 'titulo': 'Editar producto'})

@login_required
def eliminar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        producto.delete()
        return redirect('lista_productos')
    return render(request, 'productos/confirmar_eliminar.html', {'producto': producto})

@login_required
def lista_categorias(request):
    categorias = Categoria.objects.all()
    return render(request, 'productos/categorias.html', {'categorias': categorias})

@login_required
def agregar_categoria(request):
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_categorias')
    else:
        form = CategoriaForm()
    return render(request, 'productos/formulario_categoria.html', {'form': form, 'titulo': 'Agregar categoría'})

@login_required
def editar_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        form = CategoriaForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            return redirect('lista_categorias')
    else:
        form = CategoriaForm(instance=categoria)
    return render(request, 'productos/formulario_categoria.html', {'form': form, 'titulo': 'Editar categoría'})

@login_required
def eliminar_categoria(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        categoria.delete()
        return redirect('lista_categorias')
    return render(request, 'productos/confirmar_eliminar_categoria.html', {'categoria': categoria})

def generar_qr(request):
    url = request.build_absolute_uri('/escanear/')
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return HttpResponse(buffer, content_type='image/png')

@login_required
def escanear(request):
    categorias = Categoria.objects.all()
    return render(request, 'productos/escanear.html', {'categorias': categorias})

@csrf_exempt
@login_required
def procesar_escaneo(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        codigo = data.get('codigo', '').strip()
        cantidad = int(data.get('cantidad', 1))

        try:
            producto = Producto.objects.get(codigo=codigo)
            producto.cantidad += cantidad
            producto.save()
            return HttpResponse(json.dumps({
                'status': 'existe',
                'nombre': producto.nombre,
                'marca': producto.marca or '',
                'cantidad_nueva': producto.cantidad
            }), content_type='application/json')
        except Producto.DoesNotExist:
            return HttpResponse(json.dumps({
                'status': 'nuevo',
                'codigo': codigo
            }), content_type='application/json')
    return HttpResponse(status=400)

@login_required
def agregar_stock(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        cantidad = int(request.POST.get('cantidad', 0))
        if cantidad > 0:
            producto.cantidad += cantidad
            producto.save()
        return redirect('lista_productos')
    return render(request, 'productos/agregar_stock.html', {'producto': producto})

@login_required
def nueva_venta(request):
    carrito = request.session.get('carrito', {})
    productos_carrito = []
    total = 0

    for producto_id, item in carrito.items():
        subtotal = item['cantidad'] * item['precio']
        total += subtotal
        productos_carrito.append({
            'id': producto_id,
            'nombre': item['nombre'],
            'marca': item['marca'],
            'cantidad': item['cantidad'],
            'precio': item['precio'],
            'subtotal': subtotal
        })

    productos = Producto.objects.all().order_by('nombre')
    return render(request, 'productos/ventas.html', {
        'productos_carrito': productos_carrito,
        'total': total,
        'productos': productos,
    })


@login_required
def agregar_item_carrito(request):
    if request.method == 'POST':
        producto_id = request.POST.get('producto_id')
        cantidad = int(request.POST.get('cantidad', 1))

        try:
            producto = Producto.objects.get(pk=producto_id)
            carrito = request.session.get('carrito', {})

            cantidad_actual = carrito.get(str(producto_id), {}).get('cantidad', 0)
            if cantidad_actual + cantidad > producto.cantidad:
                request.session['error'] = f"Stock insuficiente. Solo hay {producto.cantidad} unidades de {producto.nombre}."
                return redirect('nueva_venta')

            if str(producto_id) in carrito:
                carrito[str(producto_id)]['cantidad'] += cantidad
            else:
                carrito[str(producto_id)] = {
                    'nombre': producto.nombre,
                    'marca': producto.marca or '',
                    'cantidad': cantidad,
                    'precio': producto.precio,
                }

            request.session['carrito'] = carrito
            request.session.modified = True
        except Producto.DoesNotExist:
            pass

    return redirect('nueva_venta')


@login_required
def eliminar_item_carrito(request, item_id):
    carrito = request.session.get('carrito', {})
    if str(item_id) in carrito:
        del carrito[str(item_id)]
        request.session['carrito'] = carrito
        request.session.modified = True
    return redirect('nueva_venta')


@login_required
def confirmar_venta(request):
    if request.method == 'POST':
        carrito = request.session.get('carrito', {})
        if not carrito:
            return redirect('nueva_venta')

        total = 0
        venta = Venta.objects.create(usuario=request.user, total=0)

        for producto_id, item in carrito.items():
            producto = Producto.objects.get(pk=producto_id)
            cantidad = item['cantidad']
            precio_unitario = item['precio']
            subtotal = cantidad * precio_unitario
            total += subtotal

            DetalleVenta.objects.create(
                venta=venta,
                producto=producto,
                cantidad=cantidad,
                precio_unitario=precio_unitario,
                subtotal=subtotal
            )

            producto.cantidad -= cantidad
            producto.save()

        venta.total = total
        venta.save()

        request.session['carrito'] = {}
        request.session.modified = True

        return redirect('detalle_venta', pk=venta.pk)

    return redirect('nueva_venta')


@login_required
def historial_ventas(request):
    ventas = Venta.objects.all().order_by('-fecha')
    return render(request, 'productos/historial_ventas.html', {'ventas': ventas})


@login_required
def detalle_venta(request, pk):
    venta = get_object_or_404(Venta, pk=pk)
    return render(request, 'productos/detalle_venta.html', {'venta': venta})

@csrf_exempt
@login_required
def crear_categoria_ajax(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        nombre = data.get('nombre', '').strip()
        if nombre:
            categoria = Categoria.objects.create(nombre=nombre)
            return HttpResponse(json.dumps({
                'success': True,
                'id': categoria.id,
                'nombre': categoria.nombre
            }), content_type='application/json')
    return HttpResponse(json.dumps({'success': False}), content_type='application/json')