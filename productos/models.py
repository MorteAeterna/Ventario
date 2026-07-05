from django.db import models

#Creacion tabla Categoria
class Categoria(models.Model):
    nombre = models.CharField(max_length=100)#Columna de nombre

    def __str__(self):
        return self.nombre
    
class Producto(models.Model):
    nombre = models.CharField(max_length=200)
    marca = models.CharField(max_length=100, blank=True, null=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True)
    cantidad = models.PositiveBigIntegerField(default=0)
    precio = models.IntegerField(default=0)
    codigo = models.CharField(max_length=50, blank=True, null=True, unique=True)
    stock_minimo = models.PositiveBigIntegerField(default=5)

    def __str__(self):
        return self.nombre

    def stock_bajo(self):
        return self.cantidad <= self.stock_minimo
    
class Venta(models.Model):
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.PositiveIntegerField(default=0)
    usuario = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Venta #{self.id} - {self.fecha.strftime('%d-%m-%Y %H:%M')}"

class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.PositiveIntegerField()
    subtotal = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.producto.nombre} x{self.cantidad}"