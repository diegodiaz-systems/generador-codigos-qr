import os
import json
import datetime
import tempfile
import subprocess
from tkinter import *
from tkinter import ttk, messagebox, simpledialog
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader

# ------------------------------
# Configuración General
# ------------------------------
MOTIVOS_FILE = "motivos.json"
OUTPUT_FOLDER = "OficiosGenerados"

# Asegura carpeta de salida
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ------------------------------
# 1. Gestión de Datos (Motivos)
# ------------------------------
def cargar_motivos():
    if not os.path.exists(MOTIVOS_FILE):
        ejemplos = [
            {"titulo": "Firma no coincide", "detalle": "La firma registrada en la documentación no coincide con nuestros registros. Es necesario acudir a sucursal para actualizar su tarjeta de firmas."},
            {"titulo": "Documentos ilegibles", "detalle": "Los archivos cargados presentan baja resolución. Favor de escanear nuevamente el INE y el Comprobante de Domicilio en formato PDF de alta calidad."}
        ]
        with open(MOTIVOS_FILE, "w", encoding="utf-8") as f:
            json.dump(ejemplos, f, indent=4, ensure_ascii=False)
        return ejemplos

    with open(MOTIVOS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def guardar_motivos(motivos):
    with open(MOTIVOS_FILE, "w", encoding="utf-8") as f:
        json.dump(motivos, f, indent=4, ensure_ascii=False)

# --- Funciones de Interfaz para Motivos ---
def agregar_motivo_dialog():
    titulo = simpledialog.askstring("Nuevo Motivo", "Título corto del motivo:")
    if not titulo: return
    detalle = simpledialog.askstring("Nuevo Motivo", "Detalle y recomendación (Texto que saldrá al escanear):")
    if not detalle: return
    
    motivos = cargar_motivos()
    motivos.append({"titulo": titulo.strip(), "detalle": detalle.strip()})
    guardar_motivos(motivos)
    actualizar_lista_motivos()

def eliminar_motivo():
    seleccionado = combo_motivos.get()
    if not seleccionado: return
    motivos = cargar_motivos()
    motivos_nuevos = [m for m in motivos if m["titulo"] != seleccionado]
    guardar_motivos(motivos_nuevos)
    actualizar_lista_motivos()
    messagebox.showinfo("Éxito", "Motivo eliminado.")

def actualizar_lista_motivos():
    motivos = cargar_motivos()
    titulos = [m["titulo"] for m in motivos]
    combo_motivos["values"] = titulos
    if titulos: combo_motivos.set(titulos[0])

# ------------------------------
# 2. Generación del Contenido QR 
# ------------------------------
def generar_texto_qr(nombre_cliente, motivo_titulo, motivo_detalle):
    fecha_hoy = datetime.datetime.now().strftime("%d/%m/%Y")
    texto = (
        f"NOTIFICACIÓN DE ESTATUS\n"
        f"Fecha: {fecha_hoy}\n"
        f"------------------------------\n\n"
        f"ESTIMADO(A): {nombre_cliente}\n\n"
        f"Le informamos que su trámite requiere atención.\n\n"
        f"MOTIVO:\n"
        f"[{motivo_titulo.upper()}]\n\n"
        f"DETALLE Y PASOS A SEGUIR:\n"
        f"{motivo_detalle}\n\n"
        f"------------------------------\n"
        f"Departamento de Créditos\n"
        f"Favor de no responder a este mensaje automático."
    )
    return texto

def generar_imagen_qr(contenido_texto, out_path):
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(contenido_texto)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(out_path)

# ------------------------------
# 3. Diseño del PDF 
# ------------------------------
def generar_pdf_oficio(nombre_cliente, qr_img_path):
    nombre_limpio = "".join([c for c in nombre_cliente if c.isalnum()])
    pdf_filename = os.path.join(OUTPUT_FOLDER, f"Aviso_{nombre_limpio}.pdf")
    
    c = canvas.Canvas(pdf_filename, pagesize=letter)
    width, height = letter
    
    # Colores
    color_primario = HexColor("#1a237e") 
    color_texto = HexColor("#333333")
    
    # --- ENCABEZADO ---
    c.setFillColor(color_primario)
    c.rect(0, height - 30, width, 30, fill=True, stroke=False)
    
    c.setFillColor(color_texto)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width/2, height - 80, "AVISO DE ESTATUS DE TRÁMITE")
    
    fecha_formal = datetime.datetime.now().strftime("%d/%m/%Y")
    c.setFont("Helvetica", 10)
    c.drawRightString(width - 50, height - 110, f"Ciudad de México, a {fecha_formal}")
    
    # --- DATOS DEL CLIENTE ---
    y = height - 160
    x = 60
    
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, "A LA ATENCIÓN DE:")
    y -= 20
    c.setFont("Helvetica", 12)
    c.drawString(x, y, nombre_cliente.upper())
    y -= 40
    
    c.line(x, y + 10, width - 60, y + 10)
    y -= 20
    
    # --- CUERPO DEL TEXTO ---
    c.setFont("Helvetica", 11)
    text_object = c.beginText(x, y)
    text_object.setLeading(18)
    
    mensaje = (
        "Por medio de la presente le informamos sobre el estatus de su solicitud. "
        "Escanee el código QR adjunto para ver el desglose detallado y las "
        "recomendaciones para continuar con su trámite."
    )
    
    palabras = mensaje.split()
    linea_actual = ""
    for palabra in palabras:
        ancho_linea = c.stringWidth(linea_actual + " " + palabra, "Helvetica", 11)
        if ancho_linea < (width - 120):
            linea_actual += " " + palabra
        else:
            text_object.textLine(linea_actual)
            linea_actual = palabra
    text_object.textLine(linea_actual)
    c.drawText(text_object)
    
    # --- ZONA DEL CÓDIGO QR ---
    qr_bg_y = y - 250
    c.setFillColor(HexColor("#f5f5f5"))
    c.roundRect(width/2 - 90, qr_bg_y, 180, 200, 10, fill=True, stroke=False)
    
    c.setFillColor(color_primario)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(width/2, qr_bg_y + 175, "DETALLE DIGITAL")
    
    try:
        qr_size = 130
        qr_x = (width - qr_size) / 2
        c.drawImage(ImageReader(qr_img_path), qr_x, qr_bg_y + 35, width=qr_size, height=qr_size)
    except Exception as e:
        print("Error al pegar QR:", e)
        
    c.setFillColor(HexColor("#666666"))
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(width/2, qr_bg_y + 20, "Use la cámara de su celular para leer")

    # --- PIE DE PÁGINA ---
    c.setFillColor(color_primario)
    c.rect(0, 0, width, 15, fill=True, stroke=False)
    
    c.setFillColor(HexColor("#888888"))
    c.setFont("Helvetica", 7)
    c.drawCentredString(width/2, 25, "Este documento es informativo y de uso interno del área de créditos.")
    
    c.showPage()
    c.save()
    return os.path.abspath(pdf_filename)

# ------------------------------
# 4. Lógica Principal
# ------------------------------
def accion_generar():
    nombre = entrada_nombre.get().strip()
    titulo_motivo = combo_motivos.get().strip()

    if not nombre or not titulo_motivo:
        messagebox.showerror("Atención", "Por favor ingresa el nombre del cliente.")
        return

    motivos = cargar_motivos()
    detalle = next((m["detalle"] for m in motivos if m["titulo"] == titulo_motivo), "")
    if not detalle:
        messagebox.showerror("Error", "Error identificando el motivo.")
        return

    try:
        contenido_qr = generar_texto_qr(nombre, titulo_motivo, detalle)
        qr_temp = os.path.join(tempfile.gettempdir(), "temp_qr_code.png")
        generar_imagen_qr(contenido_qr, qr_temp)
        pdf_path = generar_pdf_oficio(nombre, qr_temp)
        try: os.remove(qr_temp) 
        except: pass

        if messagebox.askyesno("Documento Generado", f"Se ha creado el archivo exitosamente.\n\n¿Deseas abrir la carpeta de salida?"):
            if os.name == 'nt':
                os.startfile(OUTPUT_FOLDER)
            else:
                subprocess.call(["open", OUTPUT_FOLDER])

    except Exception as e:
        messagebox.showerror("Error", f"Ocurrió un problema: {e}")

# ------------------------------
# 5. Interfaz Gráfica (GUI)
# ------------------------------
root = Tk()
root.title("Generador de Avisos de Crédito")
root.geometry("540x400")
root.resizable(False, False)
# Fondo General
root.configure(bg="#e8eaed")

# --- ESTILOS TTK ---
style = ttk.Style()
style.theme_use('clam')
style.configure("TCombobox", fieldbackground="white", background="white")

# --- TARJETA PRINCIPAL ---
card = Frame(root, bg="white", bd=1, relief="solid")
card.place(relx=0.5, rely=0.5, anchor="center", width=480, height=350)
# Ajuste visual del borde
card.configure(highlightbackground="#cccccc", highlightthickness=0)

# Encabezado
Label(card, text="Emisión de Notificaciones", font=("Helvetica", 16, "bold"), 
      bg="white", fg="#1a237e").pack(pady=(25, 20))

# --- AREA DE INPUTS ---
frame_inputs = Frame(card, bg="white")
frame_inputs.pack(pady=5)

# Input NOMBRE (CORREGIDO: Fondo gris oscuro para resaltar)
Label(frame_inputs, text="Nombre del Cliente:", font=("Helvetica", 10, "bold"), 
      bg="white", fg="#333").grid(row=0, column=0, sticky="w", padx=5)

# Aquí el cambio: bg="#e1e4e8" (Gris concreto) y borde negro sólido
entrada_nombre = Entry(frame_inputs, width=32, font=("Helvetica", 11), 
                       bg="#e1e4e8", fg="black", relief="solid", bd=1)
entrada_nombre.grid(row=1, column=0, pady=(5, 15), padx=5, ipady=4)

# Input MOTIVO
Label(frame_inputs, text="Motivo del Estatus:", font=("Helvetica", 10, "bold"), 
      bg="white", fg="#333").grid(row=2, column=0, sticky="w", padx=5)
combo_motivos = ttk.Combobox(frame_inputs, width=30, state="readonly", font=("Helvetica", 11))
combo_motivos.grid(row=3, column=0, pady=(5, 10), padx=5, ipady=3)

# --- BOTONES ---
frame_tools = Frame(card, bg="white")
frame_tools.pack(pady=5)

btn_add = Button(frame_tools, text="✚ Nuevo Motivo", command=agregar_motivo_dialog, 
                 bg="#e8eaf6", fg="#1a237e", font=("Helvetica", 9), relief="flat", padx=10)
btn_add.pack(side=LEFT, padx=5)

btn_del = Button(frame_tools, text="✖ Borrar Motivo", command=eliminar_motivo, 
                 bg="#ffebee", fg="#c62828", font=("Helvetica", 9), relief="flat", padx=10)
btn_del.pack(side=LEFT, padx=5)

# --- BOTÓN PRINCIPAL (CORREGIDO) ---
# Cambio: Texto negro para asegurar contraste y highlightbackground para Mac
btn_gen = Button(card, text="GENERAR DOCUMENTO PDF", command=accion_generar, 
                 bg="#1a237e",                  # Fondo azul (Windows/Linux)
                 highlightbackground="#1a237e", # Fondo azul (Mac)
                 fg="white",                    # Texto Blanco
                 activebackground="#002255",
                 font=("Helvetica", 11, "bold"), 
                 relief="flat", cursor="hand2")
btn_gen.pack(side=BOTTOM, fill="x", padx=30, pady=25, ipady=5)

actualizar_lista_motivos()
root.mainloop()