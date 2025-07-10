import auto_updater
auto_updater.autoactualizar()

import flet as ft
from flet import Icons
from datetime import datetime , timedelta
from dateutil.relativedelta import relativedelta
from functools import partial
import json
import os
import sys


clientes = []
ARCHIVO_CLIENTES = "clientes.json"

def guardar_clientes_json(clientes):
    try:
        with open(ARCHIVO_CLIENTES, "w", encoding="utf-8") as f:
            json.dump(clientes, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error al guardar clientes: {e}")

def cargar_clientes_json():
    if os.path.exists(ARCHIVO_CLIENTES):
        try:
            with open(ARCHIVO_CLIENTES, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # Normalizamos campos vacíos
                for c in data:
                    c["monto"] = c.get("monto", "0") or "0"
                    c["interes"] = c.get("interes", "0") or "0"
                    c["interes_mora"] = c.get("interes_mora", "0") or "0"
                    c["cuota"] = c.get("cuota", "1") or "1"
                    c["fecha_inicio"] = c.get("fecha_inicio", "") or ""
                    c["fecha_cobro"] = c.get("fecha_cobro", "") or ""
                    c["estado"] = c.get("estado", "en curso")
                    
                return data
        except Exception as e:
            print(f"Error al cargar clientes: {e}")
            return []
    else:
        return []


def parsear_fecha(fecha_str):
    if not fecha_str.strip():
        raise ValueError("Fecha vacía")
        
    formatos = ["%d-%m-%Y", "%d/%m/%Y", "%d %m %Y"]
    for formato in formatos:
        try:
            return datetime.strptime(fecha_str, formato)
        except ValueError:
            continue
    raise ValueError(f"Formato de fecha inválido: {fecha_str}")


def calcular_fecha_cobro(fecha_inicio_str, cuotas):
    try:
        fecha_inicio = parsear_fecha(fecha_inicio_str)
        # Agregar 30 días a la fecha de inicio como mínimo
        fecha_cobro_minima = fecha_inicio + timedelta()
        # Calcular fecha según cuotas
        fecha_cobro_cuotas = fecha_inicio + relativedelta(months=int(cuotas))
        
        # Usar la fecha mayor entre las dos
        fecha_cobro = max(fecha_cobro_minima, fecha_cobro_cuotas)
        
        return fecha_cobro.strftime("%d-%m-%Y")
    except Exception as e:
        print(f"Error en calcular_fecha_cobro: {e}")
        return fecha_inicio_str

def actualizar_estados_y_vencimientos():
    hoy = datetime.today().date()
    for cliente in clientes:
        try:
            fecha_inicio = datetime.strptime(cliente["fecha_inicio"], "%d-%m-%Y").date()
            fecha_cobro_actual = parsear_fecha(cliente["fecha_cobro"]).date()
            cuotas = int(cliente["cuota"])
            meses_transcurridos = (hoy.year - fecha_inicio.year) * 12 + (hoy.month - fecha_inicio.month)
            if hoy.day > fecha_inicio.day:
                meses_transcurridos += 1
            meses_transcurridos = max(0, meses_transcurridos)
            if fecha_cobro_actual < hoy:
                nueva_fecha_cobro = fecha_inicio
                for i in range(1, meses_transcurridos + 2):
                    nueva_fecha_cobro = fecha_inicio + relativedelta(months=i)
                    if nueva_fecha_cobro > hoy:
                        break
                cliente["fecha_cobro"] = nueva_fecha_cobro.strftime("%d-%m-%Y")
            if meses_transcurridos >= cuotas:
                cliente["estado"] = "completado"
                cliente["mostrar_en_general"] = False
            else:
                fecha_cobro = parsear_fecha(cliente["fecha_cobro"]).date()
                if fecha_cobro < hoy:
                    cliente["estado"] = "atrasado"
                else:
                    cliente["estado"] = "en curso"
                cliente["mostrar_en_general"] = True
        except Exception as e:
            print(f"Error actualizando estado de {cliente.get('nombre', '')}: {e}")
            cliente["mostrar_en_general"] = True
def calcular_monto_final(cliente):
    try:
        monto = float(cliente["monto"]) if cliente["monto"].strip() else 0.0
        interes = float(cliente["interes"]) if cliente["interes"].strip() else 0.0
        cuota = int(cliente["cuota"]) if cliente["cuota"].strip() else 1
        monto_final = monto * ((1 + interes/100) ** cuota)
        return monto_final
    except Exception as e:
        print(f"Error en calcular monto final para {cliente.get('nombre', '')}: {e}")
        return 0.0

def calcular_ganancia_mensual(clientes):
    hoy = datetime.today().date()
    ganancia_mes = 0.0

    for cliente in clientes:
        if cliente.get("estado") in ("completado", "pagado"):
            continue

        try:
            monto = float(cliente["monto"])
            interes = float(cliente["interes"])
            cuotas = int(cliente["cuota"])
            fecha_inicio = datetime.strptime(cliente["fecha_inicio"], "%d-%m-%Y").date()

            meses_transcurridos = (hoy.year - fecha_inicio.year) * 12 + (hoy.month - fecha_inicio.month) + 1
            if meses_transcurridos < 1 or meses_transcurridos > cuotas:
                continue  # Fuera del rango de cuotas

            monto_total = monto * ((1 + interes / 100) ** cuotas)
            cuota_mensual = monto_total / cuotas
            capital_mensual = monto / cuotas
            interes_mensual = cuota_mensual - capital_mensual

            ganancia_mes += interes_mensual

        except Exception as e:
            print(f"Error al calcular ganancia mensual para {cliente.get('nombre', '')}: {e}")
            continue

    return ganancia_mes
def calcular_cuota_mensual(cliente):
    """
    Calcula la cuota que debería estar pagando el cliente según fecha de inicio y fecha actual.
    Retorna (nro_cuota_actual, monto_cuota).
    """
    try:
        fecha_inicio = parsear_fecha(cliente["fecha_inicio"]).date()
        fecha_actual = datetime.today().date()
        
        # Si el préstamo aún no empezó, cuota 0
        if fecha_actual < fecha_inicio:
            return 0, 0
        
        # Calculamos la cantidad de meses completos entre inicio y hoy
        meses_transcurridos = (fecha_actual.year - fecha_inicio.year) * 12 + (fecha_actual.month - fecha_inicio.month)

        # Si el día actual ya pasó el día de cobro, se suma la cuota de este mes
        if fecha_actual.day >= fecha_inicio.day:
            cuota_actual = meses_transcurridos + 1
        else:
            cuota_actual = meses_transcurridos

        cuota_total = int(cliente["cuota"])
        cuota_actual = min(cuota_actual, cuota_total)  # No puede superar las cuotas totales
        
        # Cálculo del monto de la cuota
        monto_prestamo = float(cliente["monto"])
        interes = float(cliente["interes"]) / 100
        monto_cuota = monto_prestamo * (1 + interes) / cuota_total

        return cuota_actual, monto_cuota

    except Exception as e:
        print(f"Error al calcular cuota mensual: {e}")
        return 0, 0

def actualizar_cuotas_actuales():
    hoy = datetime.today().date()
    for cliente in clientes:
        try:
            fecha_inicio = datetime.strptime(cliente["fecha_inicio"], "%d-%m-%Y").date()
            cuotas = int(cliente["cuota"])
            meses_transcurridos = (hoy.year - fecha_inicio.year) * 12 + (hoy.month - fecha_inicio.month) + 1
            cuota_actual = min(max(1, meses_transcurridos), cuotas)
            cliente["cuota_actual"] = cuota_actual
        except Exception as e:
            print(f"Error actualizando cuota de {cliente.get('nombre', '')}: {e}")
            cliente["cuota_actual"] = 1

def calcular_cuota_vencida_con_interes_extra(cliente, interes_extra=0.0):
    try:
        monto = float(cliente["monto"]) if cliente["monto"].strip() else 0.0
        interes = float(cliente["interes"]) if cliente["interes"].strip() else 0.0
        cuotas = int(cliente["cuota"]) if cliente["cuota"].strip() else 1

        # Cálculo de monto total con interés compuesto
        monto_total = monto * ((1 + interes/100) ** cuotas)
        cuota_sin_mora = monto_total / cuotas if cuotas > 0 else 0

        # Aplicar interés extra solo sobre esa cuota vencida
        cuota_con_mora = cuota_sin_mora * (1 + interes_extra / 100)

        return cuota_sin_mora, cuota_con_mora

    except Exception as e:
        print(f"Error al calcular cuota vencida: {e}")
        return 0.0, 0.0


def obtener_pagos_atrasados(clientes):
    hoy = datetime.today().date()
    atrasados = []

    for c in clientes:
        try:
            fecha_cobro = datetime.strptime(c["fecha_cobro"], "%d-%m-%Y").date()
            if fecha_cobro < datetime.now() and c["estado"] == "atrasado":
                atrasados.append(f"{c['nombre']} - {fecha_cobro.strftime('%d-%m-%Y')}")
        except Exception as e:
            print(f"Error al procesar cliente atrasado {c.get('nombre', '')}: {e}")
            continue

    return atrasados


def generar_fecha_cobro():
    fecha_cobro = datetime.now() + timedelta(days=30)
    return fecha_cobro.strftime("%d-%m-%Y")

def filtrar_clientes(clientes, filtro):
    filtro = filtro.lower()
    filtrados = []
    for c in clientes:
        try:
            nombre = c.get("nombre", "").lower()
            dni = c.get("dni", "").lower()
            fecha_inicio = c.get("fecha_inicio", "").lower()
            if filtro in nombre or filtro in dni or filtro in fecha_inicio:
                filtrados.append(c)
        except:
            continue
    return filtrados

def obtener_proximos_pagos(clientes):
    hoy = datetime.today()
    proximos = []
    for c in clientes:
        try:
            monto = float(c["monto"])
            interes = float(c["interes"])
            cuotas = int(c["cuota"])
            estado = c["estado"]
            fecha_inicio = parsear_fecha(c["fecha_inicio"])
            if estado not in ["en curso", "atrasado"]:
                continue
            for i in range(cuotas):
                fecha_cuota = fecha_inicio + relativedelta(months=i)
                if fecha_cuota >= hoy:
                    proximos.append(f"{c['nombre']}: Cuota {i+1} - {fecha_cuota.strftime('%d/%m/%Y')} - ${monto * (1 + interes/100):.2f}")
                    break
        except:
            continue
    return proximos

def obtener_pagos_atrasados(clientes):
    hoy = datetime.today().date()
    atrasados = []
    for c in clientes:
        try:
            monto = float(c["monto"])
            interes = float(c["interes"])
            cuotas = int(c["cuota"])
            estado = c["estado"]
            fecha_inicio = parsear_fecha(c["fecha_inicio"]).date()
            fecha_cobro = parsear_fecha(c["fecha_cobro"]).date()
            
            if estado != "atrasado":
                continue
            
            # Calcular monto total con interés compuesto
            monto_total = monto * ((1 + interes/100) ** cuotas)
            cuota_mensual = monto_total / cuotas
            
            # Calcular qué cuota corresponde a la fecha de cobro actual
            meses_desde_inicio = (fecha_cobro.year - fecha_inicio.year) * 12 + (fecha_cobro.month - fecha_inicio.month)
            numero_cuota = min(meses_desde_inicio + 1, cuotas)
            
            # Solo mostrar si la fecha de cobro ya pasó
            if fecha_cobro < hoy and numero_cuota <= cuotas:
                dias_atraso = (hoy - fecha_cobro).days
                atrasados.append(f"{c['nombre']}: Cuota {numero_cuota} - {fecha_cobro.strftime('%d/%m/%Y')} - ${cuota_mensual:.2f} ({dias_atraso} días de atraso)")
                
        except Exception as e:
            print(f"Error al procesar pago atrasado de {c.get('nombre', '')}: {e}")
            continue
    
    return atrasados

def obtener_pagados(clientes):
    pagados = []
    for c in clientes:
        try:
            if c["estado"] == "completado":
                pagados.append(f"{c['nombre']} - Total: ${float(c['monto']):.2f}")
        except:
            continue
    return pagados

def calcular_totales(clientes):
    total_prestado = 0
    total_completados = 0
    total_por_cobrar = 0
    ganancia_total = 0
    ganancia_mensual = 0
    hoy = datetime.today()

    for c in clientes:
        try:
            monto = float(c["monto"])
            interes = float(c["interes"])
            cuotas = int(c["cuota"])
            estado = c["estado"]
            fecha_inicio = parsear_fecha(c["fecha_inicio"])

            total_prestado += monto
            if estado == "completado":
                total_completados += monto

            cuota_mensual = monto * (1 + interes / 100)
            for i in range(cuotas):
                fecha_cuota = fecha_inicio + relativedelta(months=i)
                if fecha_cuota.month == hoy.month and fecha_cuota.year == hoy.year:
                    if estado in ["en curso", "atrasado"]:
                        total_por_cobrar += cuota_mensual
                        ganancia_mensual += monto * (interes / 100)
                    break

            ganancia_total += monto * (interes / 100) * cuotas

        except:
            continue

    return total_prestado, total_completados, total_por_cobrar, ganancia_total, ganancia_mensual

def calcular_total_atrasado(cliente):
    try:
        hoy = datetime.today().date()
        fecha_cobro = parsear_fecha(cliente["fecha_cobro"]).date()
        interes_mora = float(cliente.get("interes_mora", "0") or "0")
        
        dias_atraso = (hoy - fecha_cobro).days
        if dias_atraso <= 0:
            return 0.0, 0  # No debe atraso

        _, cuota_mensual = calcular_cuota_mensual(cliente)
        cuota_con_mora = cuota_mensual * (1 + interes_mora / 100)
        
        return cuota_con_mora, dias_atraso

    except Exception as e:
        print(f"Error al calcular total atrasado para {cliente.get('nombre', '')}: {e}")
        return 0.0, 0

def vista_general(page, clientes):
    filtro_text = ft.TextField(label="Buscar por nombre, DNI o fecha (dd/mm/yyyy)", width=400)

    resumen_contenedor = ft.Container()
    listas_contenedor = ft.Container()

    def actualizar_vista(clientes_filtrados):
        total_prestado, total_completados, total_por_cobrar, ganancia_total, ganancia_mensual = calcular_totales(clientes_filtrados)
        hoy = datetime.today().date()

        def marcar_pagado(cliente, cuota_num):
            try:
                if "estado_cuotas" not in cliente:
                    cliente["estado_cuotas"] = ["pendiente"] * int(cliente["cuota"])

                cliente["estado_cuotas"][cuota_num - 1] = "pagada"
                cliente["cuotas_pagadas"] = cliente["estado_cuotas"].count("pagada")
                cuotas_totales = int(cliente["cuota"])

                if cliente["cuotas_pagadas"] >= cuotas_totales:
                    cliente["estado"] = "completado"
                else:
                    cliente["estado"] = "en curso"

                fecha_inicio = parsear_fecha(cliente["fecha_inicio"]).date()
                nueva_fecha_cobro = fecha_inicio + relativedelta(months=cliente["cuotas_pagadas"])
                cliente["fecha_cobro"] = nueva_fecha_cobro.strftime("%d-%m-%Y")

                guardar_clientes_json(clientes)
                actualizar()
            except Exception as e:
                print(f"Error al marcar pagado: {e}")

        # Próximos pagos
        items_pagos = []
        for c in clientes_filtrados:
            cuotas_totales = int(c["cuota"])
            fecha_inicio = parsear_fecha(c["fecha_inicio"]).date()

            for cuota_num in range(1, cuotas_totales + 1):
                fecha_cuota = fecha_inicio + relativedelta(months=cuota_num - 1)
                
                if fecha_cuota >= hoy and fecha_cuota.month == hoy.month and fecha_cuota.year == hoy.year:
                    texto = f"{c['nombre']} - {fecha_cuota.strftime('%d-%m-%Y')} - Cuota {cuota_num}/{cuotas_totales}"
                    items_pagos.append(ft.Text(texto, color="white", size=14))
                    break  # Solo mostrar la próxima del mes actual

        if not items_pagos:
            items_pagos = [ft.Text("No hay próximos pagos", color="white")]

        # Pagos atrasados
        items_atrasados = []
        for c in clientes_filtrados:
            cuotas_totales = int(c["cuota"])
            cuotas_pagadas = c.get("cuotas_pagadas", 0)
            fecha_inicio = parsear_fecha(c["fecha_inicio"]).date()
            monto_total = float(c["monto"])
            interes_mensual_pct = float(c.get("interes", 0))
            interes_mora_diario_pct = float(c.get("interes_mora", 0))

            if "estado_cuotas" not in c:
                c["estado_cuotas"] = ["pendiente"] * cuotas_totales

            for cuota_num in range(1, cuotas_totales + 1):
                if c["estado_cuotas"][cuota_num - 1] == "pendiente":
                    fecha_cuota = fecha_inicio + relativedelta(months=cuota_num - 1)
                    dias_atraso = (hoy - fecha_cuota).days

                    if dias_atraso > 0:
                        cuota_base = monto_total / cuotas_totales
                        interes_mensual = cuota_base * (interes_mensual_pct / 100)
                        interes_mora = cuota_base * (interes_mora_diario_pct / 100) * dias_atraso
                        monto_adeudado = cuota_base + interes_mensual + interes_mora

                        texto = (
                            f"{c['nombre']} - Cuota {cuota_num}/{cuotas_totales} vencida hace {dias_atraso} días - "
                            f"Monto adeudado: ${monto_adeudado:,.2f}"
                        )

                        # Solución para evitar problemas de captura de variables en el lambda
                        def crear_checkbox(cliente_ref, cuota_ref):
                            return ft.Checkbox(
                                label="Pagar",
                                on_change=lambda e: marcar_pagado(cliente_ref, cuota_ref)
                            )

                        items_atrasados.append(
                            ft.Row([
                                ft.Text(texto, color="white", size=14, expand=True),
                                crear_checkbox(c, cuota_num)
                            ])
                        )

        if not items_atrasados:
            items_atrasados = [ft.Text("No hay pagos atrasados", color="white")]

        # Clientes que ya completaron pagos
        lista_pagados = obtener_pagados(clientes_filtrados) or []
        items_pagados = [ft.Text(pago, color="white", size=14) for pago in lista_pagados] if lista_pagados else [ft.Text("Ningún cliente completó pagos", color="white")]

        # Actualizar resumen
        resumen_contenedor.content = ft.ResponsiveRow([
            ft.Container(
                content=ft.Column([
                    ft.Text("Total Prestado", size=16, weight="bold", color="white", text_align=ft.TextAlign.CENTER),
                    ft.Text(f"${total_prestado:,.2f}", size=22, weight="bold", color="white", text_align=ft.TextAlign.CENTER)
                ], alignment=ft.MainAxisAlignment.CENTER),
                bgcolor="#1976D2",
                padding=ft.padding.all(20),
                expand=True,
                height=120,
                border_radius=12,
                margin=ft.margin.all(6)
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("Total Cobrado", size=16, weight="bold", color="white", text_align=ft.TextAlign.CENTER),
                    ft.Text(f"${total_completados:,.2f}", size=22, weight="bold", color="white", text_align=ft.TextAlign.CENTER)
                ], alignment=ft.MainAxisAlignment.CENTER),
                bgcolor="#388E3C",
                padding=ft.padding.all(20),
                expand=True,
                height=120,
                border_radius=12,
                margin=ft.margin.all(6)
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("Total Por Cobrar", size=16, weight="bold", color="white", text_align=ft.TextAlign.CENTER),
                    ft.Text(f"${total_por_cobrar:,.2f}", size=22, weight="bold", color="white", text_align=ft.TextAlign.CENTER)
                ], alignment=ft.MainAxisAlignment.CENTER),
                bgcolor="#FBC02D",
                padding=ft.padding.all(20),
                expand=True,
                height=120,
                border_radius=12,
                margin=ft.margin.all(6)
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("Ganancia Total", size=16, weight="bold", color="white", text_align=ft.TextAlign.CENTER),
                    ft.Text(f"${ganancia_total:,.2f}", size=22, weight="bold", color="white", text_align=ft.TextAlign.CENTER)
                ], alignment=ft.MainAxisAlignment.CENTER),
                bgcolor="#D32F2F",
                padding=ft.padding.all(20),
                expand=True,
                height=120,
                border_radius=12,
                margin=ft.margin.all(6)
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("Ganancia Mensual", size=16, weight="bold", color="white", text_align=ft.TextAlign.CENTER),
                    ft.Text(f"${ganancia_mensual:,.2f}", size=22, weight="bold", color="white", text_align=ft.TextAlign.CENTER)
                ], alignment=ft.MainAxisAlignment.CENTER),
                bgcolor="#F57C00",
                padding=ft.padding.all(20),
                expand=True,
                height=120,
                border_radius=12,
                margin=ft.margin.all(6)
            ),
        ], spacing=15)

        # Actualizar listas
        listas_contenedor.content = ft.Row([
            ft.Container(
                content=ft.Column(
                    [ft.Text("Próximos Pagos", size=20, weight="bold", color="white"),
                     ft.Divider(color="white")] + items_pagos,
                    spacing=6,
                    scroll=ft.ScrollMode.AUTO,
                    height=300,
                ),
                expand=True,
                padding=10,
                bgcolor="#455A64",
            ),
            ft.Container(
                content=ft.Column(
                    [ft.Text("Pagos Atrasados", size=20, weight="bold", color="white"),
                     ft.Divider(color="white")] + items_atrasados,
                    spacing=6,
                    scroll=ft.ScrollMode.AUTO,
                    height=300,
                ),
                expand=True,
                padding=10,
                bgcolor="#B71C1C",
            ),
            ft.Container(
                content=ft.Column(
                    [ft.Text("Clientes que ya pagaron", size=20, weight="bold", color="white"),
                     ft.Divider(color="white")] + items_pagados,
                    spacing=6,
                    scroll=ft.ScrollMode.AUTO,
                    height=300,
                ),
                expand=True,
                padding=10,
                bgcolor="#2E7D32",
            ),
        ], spacing=12, expand=True)

        page.update()

    def actualizar(e=None):
        filtro = filtro_text.value.strip()
        clientes_filtrados = filtrar_clientes(clientes, filtro) if filtro else clientes
        actualizar_vista(clientes_filtrados)

    filtro_text.on_change = actualizar

    contenedor_principal = ft.Container(
        content=ft.Column([
            ft.Text("Vista General", size=28, weight="bold", color="white"),
            filtro_text,
            ft.Container(
                content=ft.Column([
                    resumen_contenedor,
                    listas_contenedor
                ], spacing=20, scroll=ft.ScrollMode.AUTO),
                expand=True
            )
        ], spacing=20),
        padding=20,
        bgcolor="#121212",
        expand=True
    )

    actualizar()
    return contenedor_principal

def obtener_proximos_pagos(clientes):
                hoy = datetime.today().date()
                proximos = []

                for c in clientes:
                    try:
                        fecha_cobro = parsear_fecha(c["fecha_cobro"]).date()

                        if fecha_cobro >= hoy:
                            proximos.append((fecha_cobro, f"{c['nombre']} - {fecha_cobro.strftime('%d-%m-%Y')}"))
                    except Exception as e:
                        print(f"Error al procesar cliente {c.get('nombre', '')}: {e}")
                        continue

                    proximos.sort(key=lambda x: x[0])
                    return [texto for _, texto in proximos[:5]]


def vista_clientes(page, clientes, on_agregar_cliente, on_editar_cliente, on_eliminar_cliente):
    filtro_text = ft.TextField(label="Buscar por nombre, DNI o teléfono", width=300, visible=False)
    lista_clientes = ft.Column(expand=True, spacing=5, scroll=ft.ScrollMode.AUTO)
    search_visible = {"value": False}
    agregado = {"value": False}  # Flag para evitar update prematuro

    def actualizar_lista(e=None, inicial=False):
        filtro = filtro_text.value.strip().lower()
        lista_clientes.controls.clear()

        clientes_filtrados = clientes
        if filtro:
            clientes_filtrados = [c for c in clientes if 
                            filtro in c.get("nombre", "").lower() or 
                            filtro in c.get("dni", "").lower() or 
                            filtro in c.get("telefono", "").lower()]

        for i, c in enumerate(clientes_filtrados, start=1):
            color_estado = {
                "en curso": "lightgreen",
                "atrasado": "red",
                "pagado": "green",
                "completado": "gray"
            }.get(c.get("estado", ""), "white")

            lista_clientes.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(
                            f"{i}. {c.get('nombre', '')} - DNI: {c.get('dni', '')} - Tel: {c.get('telefono', '')} - Monto: ${c.get('monto', '')} - Estado: {c.get('estado', '')}",
                            color=color_estado,
                            expand=True
                        ),
                        ft.IconButton(
                            icon=ft.Icons.EDIT,
                            tooltip="Editar",
                            on_click=partial(on_editar_cliente, i-1)
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE,
                            tooltip="Eliminar",
                            on_click=partial(on_eliminar_cliente, i-1)
                        ),
                    ]),
                    padding=ft.padding.all(5),
                    margin=ft.margin.all(5),
                )
            )
        if agregado["value"]:
            page.update()

    def toggle_search(e):
        search_visible["value"] = not search_visible["value"]
        filtro_text.visible = search_visible["value"]
        if not search_visible["value"]:
            filtro_text.value = ""
            actualizar_lista(e)
        page.update()

    filtro_text.on_change = actualizar_lista

    barra_superior = ft.Container(
        content=ft.Row([
            ft.Text("Clientes", size=24, weight="bold", color="white"),
            ft.Row([
                ft.ElevatedButton("Agregar nuevo cliente", icon=ft.Icons.PERSON_ADD, on_click=on_agregar_cliente),
                filtro_text,
                ft.IconButton(
                    icon=ft.Icons.SEARCH,
                    tooltip="Buscar",
                    on_click=toggle_search
                ),
            ], spacing=10),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=ft.padding.symmetric(horizontal=20, vertical=10),
        bgcolor="#333333",
    )

    contenedor_principal = ft.Container(
        content=ft.Column([
            barra_superior,
            ft.Container(
                content=ft.Column([
                    ft.Divider(thickness=1, color="gray"),
                    ft.Text("Lista de clientes:", color="white", weight="bold"),
                    lista_clientes,
                ], spacing=10, scroll=ft.ScrollMode.AUTO),
                padding=20,
                expand=True
            )
        ], spacing=0),
        expand=True
    )

    agregado["value"] = True
    actualizar_lista(inicial=True)

    return contenedor_principal

def vista_formulario_cliente(on_guardar, on_cancelar, cliente=None):
    # Inputs
    input_nombre = ft.TextField(label="Nombre", width=300, value=cliente["nombre"] if cliente else "")
    input_dni = ft.TextField(label="DNI", width=300, value=cliente["dni"] if cliente else "")
    input_telefono = ft.TextField(label="Teléfono", width=300, value=cliente["telefono"] if cliente else "")
    input_monto = ft.TextField(label="Monto", width=300, value=cliente["monto"] if cliente else "")
    input_cuota = ft.TextField(label="Cantidad de cuotas (meses)", width=300, value=cliente["cuota"] if cliente else "")
    input_intmens = ft.TextField(label="Intereses mensuales (%)", width=300, value=cliente["interes"] if cliente else "")
    input_interes_mora = ft.TextField(label="Interés adicional por atraso (%)", width=300, value=cliente["interes_mora"] if cliente and "interes_mora" in cliente else "")
    input_fechaini = ft.TextField(label="Fecha de inicio (dd-mm-aaaa)", width=300, value=cliente["fecha_inicio"] if cliente else "")
    input_fechacobro = ft.TextField(label="Fecha de cobro (dd-mm-aaaa)", width=240, value=cliente["fecha_cobro"] if cliente else "")
    input_cuotas_pagadas = ft.TextField(label="Cantidad de cuotas ya pagadas", width=300, value=str(cliente.get("cuotas_pagadas", 0)) if cliente else "0")
    input_estado = ft.Dropdown(
        label="Estado",
        width=300,
        value=cliente["estado"] if cliente else "en curso",
        options=[
            ft.dropdown.Option("en curso"),
            ft.dropdown.Option("atrasado"),
            ft.dropdown.Option("pagado"),
            ft.dropdown.Option("completado"),
        ]
    )

    def mostrar_error(page, mensaje):
        page.snack_bar = ft.SnackBar(ft.Text(mensaje), open=True)
        page.update()

    def generar_fecha_automatica(e):
        try:
            hoy = datetime.today()
            fecha_cobro = hoy + relativedelta(months=1)
            if hoy.day > 28:
                fecha_cobro = fecha_cobro.replace(day=1) + relativedelta(months=1) - timedelta(days=1)
            input_fechacobro.value = fecha_cobro.strftime("%d-%m-%Y")
            input_estado.value = "en curso"
            input_estado.update()
            e.page.update()
        except Exception as ex:
            mostrar_error(e.page, f"Error al generar fecha: {str(ex)}")

    def handle_guardar(e):
        try:
            cuotas_pagadas_input = input_cuotas_pagadas.value.strip() or "0"
            if not cuotas_pagadas_input.isdigit():
                mostrar_error(e.page, "Cuotas pagadas debe ser un número entero.")
                return
            cuotas_pagadas = int(cuotas_pagadas_input)

            nuevo_cliente = {
                "nombre": input_nombre.value,
                "dni": input_dni.value,
                "telefono": input_telefono.value,
                "monto": input_monto.value,
                "cuota": input_cuota.value,
                "interes": input_intmens.value,
                "interes_mora": input_interes_mora.value,
                "fecha_inicio": input_fechaini.value,
                "fecha_cobro": input_fechacobro.value,
                "estado": input_estado.value
            }

            cuotas_totales = int(nuevo_cliente["cuota"])
            # Actualizar estado general según cuotas pagadas
            if cuotas_pagadas == 0:
                    nuevo_cliente["estado"] = "en curso"
            elif cuotas_pagadas < cuotas_totales:
                nuevo_cliente["estado"] = "pagado"
            else:
                nuevo_cliente["estado"] = "completado"


            if not cliente:
                nuevo_cliente["estado_cuotas"] = ["pendiente"] * cuotas_totales
                for i in range(cuotas_pagadas):
                    nuevo_cliente["estado_cuotas"][i] = "pagada"
                nuevo_cliente["cuotas_pagadas"] = cuotas_pagadas
                try:
                    fecha_inicio = parsear_fecha(nuevo_cliente["fecha_inicio"]).date()
                    nueva_fecha_cobro = fecha_inicio + relativedelta(months=cuotas_pagadas)
                    nuevo_cliente["fecha_cobro"] = nueva_fecha_cobro.strftime("%d-%m-%Y")
                except Exception:
                    pass
                nuevo_cliente["estado"] = "completado" if cuotas_pagadas >= cuotas_totales else "en curso"
            else:
                nuevo_cliente["cuotas_pagadas"] = cuotas_pagadas
                estado_cuotas = cliente.get("estado_cuotas", ["pendiente"] * cuotas_totales)
                for i in range(cuotas_totales):
                    estado_cuotas[i] = "pagada" if i < cuotas_pagadas else "pendiente"
                nuevo_cliente["estado_cuotas"] = estado_cuotas
                nuevo_cliente["estado"] = "completado" if cuotas_pagadas >= cuotas_totales else input_estado.value

            on_guardar(nuevo_cliente)
            e.page.update()

        except Exception as ex:
            mostrar_error(e.page, f"Error al guardar: {str(ex)}")

    # Acá se usa la función que ya está definida más arriba 👇
    boton_generar_fecha = ft.IconButton(icon=Icons.DATE_RANGE, tooltip="Generar Fecha Automática", on_click=generar_fecha_automatica)
    btn_guardar = ft.ElevatedButton("Guardar", on_click=handle_guardar)
    btn_cancelar = ft.ElevatedButton("Cancelar", on_click=on_cancelar)

    return ft.Container(
        expand=True,
        padding=20,
        bgcolor="#222222",
        content=ft.Column([
            ft.Text("Formulario de Cliente", size=24, weight="bold", color="white"),
            ft.Container(
                expand=True,
                height=500,
                content=ft.Column([
                    input_nombre,
                    input_dni,
                    input_telefono,
                    input_monto,
                    input_cuota,
                    input_intmens,
                    input_interes_mora,
                    input_fechaini,
                    ft.Row([input_fechacobro, boton_generar_fecha], spacing=10),
                    input_cuotas_pagadas,
                    input_estado,
                    ft.Row([btn_guardar, btn_cancelar], spacing=10),
                ], spacing=15, scroll=ft.ScrollMode.ALWAYS),
                bgcolor="#333333",
                border_radius=10,
                padding=15,
            )
        ], spacing=20)
    )

def main(page: ft.Page):
    page.title = "Sistema de Préstamos"
    page.bgcolor = "#222222"
    page.window_width = 900
    page.window_height = 600

    global clientes
    clientes = cargar_clientes_json()

    current_view = {"vista": "lista"}
    cliente_editando = {"index": None}

    cont_principal = ft.Container(expand=True)

    def eliminar_cliente(index, e=None):
        if 0 <= index < len(clientes):
            del clientes[index]
            guardar_clientes_json(clientes)
            mostrar_vista_clientes()
        if e:
            e.page.update()
        else:
            page.update()

    def mostrar_vista_general(e=None):
        current_view["vista"] = "general"
        cont_principal.content = vista_general(page, clientes)
        page.update()

    def mostrar_formulario_agregar(e=None):
        cliente_editando["index"] = None
        current_view["vista"] = "formulario"
        cont_principal.content = vista_formulario_cliente(
            on_guardar=guardar_y_volver,
            on_cancelar=mostrar_vista_clientes,
        )
        if e:
            e.page.update()
        else:
            page.update()

    def mostrar_formulario_editar(index, e=None):
        cliente_editando["index"] = index
        current_view["vista"] = "formulario"
        cont_principal.content = vista_formulario_cliente(
            on_guardar=guardar_cliente_interno,
            on_cancelar=mostrar_vista_clientes,
            cliente=clientes[index]
        )
        if e:
            e.page.update()
        else:
            page.update()

# File: a.py
    def mostrar_vista_clientes(e=None):
        current_view["vista"] = "lista"
        cont_principal.content = vista_clientes(
            page, # Add page here
            clientes,
            on_agregar_cliente=mostrar_formulario_agregar,
            on_editar_cliente=mostrar_formulario_editar,
            on_eliminar_cliente=eliminar_cliente
        )
        page.update()

        current_view["vista"] = "lista"
        cont_principal.content = vista_clientes(
            page, # Add page here
            clientes,
            on_agregar_cliente=mostrar_formulario_agregar,
            on_editar_cliente=mostrar_formulario_editar,
            on_eliminar_cliente=eliminar_cliente
        )
        page.update()

    def guardar_cliente_interno(nuevo_cliente):
        guardar_cliente(nuevo_cliente)
        mostrar_vista_clientes()
        page.update()

    def guardar_cliente(nuevo_cliente):
        idx = cliente_editando["index"]

        if not nuevo_cliente.get("fecha_cobro"):
            nuevo_cliente["fecha_cobro"] = calcular_fecha_cobro(nuevo_cliente["fecha_inicio"], nuevo_cliente["cuota"])

        try:
            fecha_cobro = parsear_fecha(nuevo_cliente["fecha_cobro"]).date()
            hoy = datetime.today().date()
            if idx is None:
                nuevo_cliente["estado"] = "atrasado" if fecha_cobro < hoy else "en curso"
            else:
                # Mantener estado previo o recalcular si querés
                nuevo_cliente["estado"] = nuevo_cliente.get("estado", "en curso")
        except Exception as e:
            print(f"Error al determinar estado: {e}")
            nuevo_cliente["estado"] = "en curso"

        try:
            if idx is None:
                clientes.append(nuevo_cliente)
            else:
                clientes[idx] = nuevo_cliente

            actualizar_estados_y_vencimientos()
            guardar_clientes_json(clientes)
            page.snack_bar = ft.SnackBar(ft.Text("Cliente guardado correctamente"), open=True)
            page.update()
        except Exception as e:
            page.snack_bar = ft.SnackBar(ft.Text(f"Error al guardar: {str(e)}"), open=True)
            page.update()

    def guardar_y_volver(nuevo_cliente):
        guardar_cliente(nuevo_cliente)
        mostrar_vista_clientes()

    # Barra lateral
    barra_lateral = ft.Column([
        ft.ElevatedButton("Vista General", on_click=mostrar_vista_general),
        ft.ElevatedButton("Clientes", on_click=mostrar_vista_clientes),
        ft.ElevatedButton("Agregar Cliente", on_click=mostrar_formulario_agregar),
    ], spacing=10)

    cont_principal.content = vista_general(page, clientes)

    page.add(
        ft.Row([
            ft.Container(barra_lateral, width=150, bgcolor="#333"),
            ft.VerticalDivider(width=1, color="gray"),
            cont_principal,
        ], expand=True)
    )

    mostrar_vista_clientes()

ft.app(target=main)
