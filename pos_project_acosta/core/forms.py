from django import forms
from .models import (
    Articulo, ListaPrecio, GrupoArticulo, LineaArticulo, 
    Empresa, Sucursal, PrecioArticuloAntiguo
)
from pos_project_acosta.choices import EstadoEntidades, TipoListaPrecio, CanalVenta


class ArticuloForm(forms.ModelForm):
    """Formulario para el modelo Articulo"""

    class Meta:
        model = Articulo
        fields = [
            'codigo_articulo', 'codigo_barras', 'descripcion', 'presentacion',
            'grupo', 'linea', 'stock'
        ]
        widgets = {
            'codigo_articulo': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo_barras': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.TextInput(attrs={'class': 'form-control'}),
            'presentacion': forms.TextInput(attrs={'class': 'form-control'}),
            'grupo': forms.Select(attrs={'class': 'form-select'}),
            'linea': forms.Select(attrs={'class': 'form-select'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filtrar solo grupos activos
        self.fields['grupo'].queryset = GrupoArticulo.objects.filter(estado=EstadoEntidades.ACTIVO)

        # Filtrar líneas activas
        self.fields['linea'].queryset = LineaArticulo.objects.filter(estado=EstadoEntidades.ACTIVO)

        # Si ya existe un grupo seleccionado, filtrar líneas por ese grupo
        if self.instance.pk and self.instance.grupo:
            self.fields['linea'].queryset = LineaArticulo.objects.filter(
                grupo=self.instance.grupo,
                estado=EstadoEntidades.ACTIVO
            )


class ListaPrecioForm(forms.ModelForm):
    """Formulario para el modelo ListaPrecio (nuevo diseño)"""

    class Meta:
        model = ListaPrecio
        fields = [
            'empresa', 'sucursal', 'nombre', 'tipo', 'canal_venta',
            'fecha_inicio', 'fecha_fin', 'estado', 'descripcion'
        ]
        widgets = {
            'empresa': forms.Select(attrs={'class': 'form-select'}),
            'sucursal': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'canal_venta': forms.Select(attrs={'class': 'form-select'}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filtrar solo empresas activas
        self.fields['empresa'].queryset = Empresa.objects.filter(estado=EstadoEntidades.ACTIVO)
        self.fields['empresa'].required = False
        
        # Filtrar solo sucursales activas
        self.fields['sucursal'].queryset = Sucursal.objects.filter(estado=EstadoEntidades.ACTIVO)
        self.fields['sucursal'].required = False
        
        # Opciones para tipo y canal
        self.fields['tipo'].choices = TipoListaPrecio.choices
        self.fields['canal_venta'].choices = [('', '---------')] + list(CanalVenta.choices)
        self.fields['canal_venta'].required = False
        
        # Opciones para estado
        self.fields['estado'].choices = EstadoEntidades.choices


class PrecioArticuloAntiguoForm(forms.ModelForm):
    """Formulario para el modelo antiguo PrecioArticuloAntiguo (compatibilidad)"""

    class Meta:
        model = PrecioArticuloAntiguo
        fields = [
            'precio_1', 'precio_2', 'precio_3', 'precio_4',
            'precio_compra', 'precio_costo'
        ]
        widgets = {
            'precio_1': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'precio_2': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'precio_3': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'precio_4': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'precio_compra': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'precio_costo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
        }