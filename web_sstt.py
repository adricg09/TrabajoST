# coding=utf-8
#!/usr/bin/env python3

import socket
import selectors    #https://docs.python.org/3/library/selectors.html
import select
import types        # Para definir el tipo de datos data
import argparse     # Leer parametros de ejecución
import os           # Obtener ruta y extension
from datetime import datetime, timedelta # Fechas de los mensajes HTTP
import time         # Timeout conexión
import sys          # sys.exit
import re           # Analizador sintáctico
import logging      # Para imprimir logs
from datetime import timezone



BUFSIZE = 8192 # Tamaño máximo del buffer que se puede utilizar
TIMEOUT_CONNECTION = 30 # Timout para la conexión persistente
MAX_ACCESOS = 10
CORREO=re.compile('adrian.cuervog%40um.es|ds.anishchenkohalkina%40um.es')
FORMATO = re.compile('GET')

# Extensiones admitidas (extension, name in HTTP)
filetypes = {"gif":"image/gif", "jpg":"image/jpg", "jpeg":"image/jpeg", "png":"image/png", "htm":"text/htm", 
             "html":"text/html", "css":"text/css", "js":"text/js", "ico":"image/x-icon"}

# Configuración de logging
logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s.%(msecs)03d] [%(levelname)-7s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger()

def error_400(route):
    #Error Bad Request
    length  = os.stat(route).st_size
    root, ext = os.path.splitext(route)
    type = filetypes[ext[1:]]
    mensaje = 'HTTP/1.1 400 Bad Request\r\n'\
    'Connection: Close\r\n'\
    'Content-Length: ' + str(length) + '\r\n'\
    'Content-Type: ' + type + '\r\n'\
    '\r\n'
    return mensaje.encode()

def error_403(route):
    #Error Forbiden
    length = os.stat(route).st_size
    root, ext = os.path.splitext(route)
    type = filetypes[ext[1:]]
    mensaje = 'HTTP/1.1 403 Forbiden\r\n'\
    'Connection: Close\r\n'\
    'Content-Length: ' + str(length) + '\r\n'\
    'Content-Type: ' + type + '\r\n'\
    '\r\n'
    return mensaje.encode()

def error_404(route):
    #Error Not-Found
    length = os.stat(route).st_size
    root, ext = os.path.splitext(route)
    type = filetypes[ext[1:]]
    mensaje = 'HTTP/1.1 404 Not Found\r\n'\
    'Connection: Close\r\n'\
    'Content-Length: ' + str(length) + '\r\n'\
    'Content-Type: ' + type + '\r\n'\
    '\r\n'
    return mensaje.encode()

def error_405(route):
    #Method not allowed
    length = os.stat(route).st_size
    root, ext = os.path.splitext(route)
    type = filetypes[ext[1:]]
    mensaje = 'HTTP/1.1 405 Method Not Allowed\r\n'\
    'Connection: Close\r\n'\
    'Content-Length: ' + str(length) + '\r\n'\
    'Content-Type: ' + type + '\r\n'\
    '\r\n'
    return mensaje.encode()

def error_505(route):
    #HTTP Version Not Supported
    length = os.stat(route).st_size
    root, ext = os.path.splitext(route)
    type = filetypes[ext[1:]]
    mensaje = 'HTTP/1.1 505 HTTP Version Not Supported\r\n'\
    'Connection: Close\r\n'\
    'Content-Length: ' + str(length) + '\r\n'\
    'Content-Type: ' + type + '\r\n'\
    '\r\n'
    return mensaje.encode()

def crear_respuesta(route):
    dt_mod = datetime.fromtimestamp(os.path.getmtime(route)).strftime('%a, %d %b %Y %H:%M:%S GMT')
    length = os.stat(route).st_size
    root, ext = os.path.splitext(route)
    type = filetypes[ext[1:]]

    mensaje = 'HTTP/1.1 200 OK\r\n'\
    'Date: ' + datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT') + '\r\n'\
    'Server: web.cazaBugs1991.org \r\n'\
    'Last-Modified: ' + dt_mod + '\r\n'\
    'Content-Length: ' + str(length) + '\r\n'\
    'Keep-Alive: timeout=' + str(TIMEOUT_CONNECTION) + ', max=' + str(MAX_ACCESOS) + '\r\n'\
    'Connection: Keep-Alive\r\n'\
    'Content-Type: ' + str(type) + '\r\n'\
    '\r\n'
    return mensaje.encode()

def crear_respuesta_index(route, counter):
    dt_mod = datetime.fromtimestamp(os.path.getmtime(route)).strftime('%a, %d %b %Y %H:%M:%S GMT')
    length = os.stat(route).st_size
    root, ext = os.path.splitext(route)
    type = filetypes[ext[1:]]

    mensaje = 'HTTP/1.1 200 OK\r\n'\
    'Date: ' + datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT') + '\r\n'\
    'Server: web.cazaBugs1991.org \r\n'\
    'Last-Modified: ' + dt_mod + '\r\n'\
    'Content-Length: ' + str(length) + '\r\n'\
    'Keep-Alive: timeout=' + str(TIMEOUT_CONNECTION) + ', max=' + str(MAX_ACCESOS) + '\r\n'\
    'Connection: Keep-Alive\r\n'\
    'Content-Type: ' + str(type) + '\r\n'\
    'Set-Cookie: cookie_counter_1991=' + str(counter) + '; max-age=30\r\n'\
    '\r\n'
    return mensaje.encode()


def enviar_mensaje(cs, data):
    """ Esta función envía datos (data) a través del socket cs
        Devuelve el número de bytes enviados.
    """
    return cs.send(data)


def recibir_mensaje(cs):
    """ Esta función recibe datos a través del socket cs
        Leemos la información que nos llega. recv() devuelve un string con los datos.
    """
    return cs.recv(BUFSIZE)


def cerrar_conexion(cs):
    """ Esta función cierra una conexión activa.
    """
    cs.close()
    print("Cerrando conexion")


def process_cookies(headers,  cs):
    """ Esta función procesa la cookie cookie_counter
        1. Se analizan las cabeceras en headers para buscar la cabecera Cookie
        2. Una vez encontrada una cabecera Cookie se comprueba si el valor es cookie_counter
        3. Si no se encuentra cookie_counter , se devuelve 1
        4. Si se encuentra y tiene el valor MAX_ACCESSOS se devuelve MAX_ACCESOS
        5. Si se encuentra y tiene un valor 1 <= x < MAX_ACCESOS se incrementa en 1 y se devuelve el valor
    """
    cookie_header = None
    for h in headers[1:]:
        if h == "":
            break
        if h.lower().startswith("cookie:"):
            cookie_header = h
            break

    if cookie_header is None:
        return 1

    m = re.search(r'cookie_counter_1991=(\d+)', cookie_header)
    if not m:
        return 1

    valor = int(m.group(1))
    if valor >= MAX_ACCESOS:
        return MAX_ACCESOS + 1
    return valor + 1

def process_web_request(cs, webroot):
    """ Procesamiento principal de los mensajes recibidos. """
    rlist = [cs]
    wlist = []

    # * Bucle para esperar hasta que lleguen datos en la red a través del socket cs con select()
    while rlist:
        rsublist, wsublist, xsublist = select.select(rlist, wlist, [], TIMEOUT_CONNECTION)

        # * Se comprueba si hay que cerrar la conexión por exceder TIMEOUT_CONNECTION segundos
        if not (wsublist or rsublist or xsublist):
            print("TIMEOUT - Cerrando conexión persistente por inactividad.")
            return # Salimos para que el proceso cierre el socket

        # * Leer los datos con recv.
        for socket_client in rsublist:
            datos = recibir_mensaje(socket_client)
            if not datos:
                # El cliente ha cerrado la conexión desde su lado
                return

            str_datos = datos.decode('utf-8', errors='ignore')
            lista_cabeceras = str_datos.split("\r\n")

            if not lista_cabeceras or lista_cabeceras[0] == "":
                continue

            # * Analizar que la línea de solicitud está bien formateada
            request_line = lista_cabeceras[0].strip()
            partes = request_line.split()

            if len(partes) != 3:
                print("Error 400 Bad Request")
                ruta_absoluta = webroot + "/400.html"
                if os.path.isfile(ruta_absoluta):
                    enviar_mensaje(cs, error_400(ruta_absoluta))
                    with open(ruta_absoluta, 'rb') as f:
                        enviar_mensaje(cs, f.read())
                return

            method, url, version = partes

            # * Imprimir cabeceras para depuración
            for cabeceras in lista_cabeceras:
                print(cabeceras)

            # * Comprobar versión HTTP y Método
            if version != "HTTP/1.1":
                print("Error 505 HTTP Version Not Supported")
                ruta_absoluta = webroot + "/505.html"
                if os.path.isfile(ruta_absoluta):
                    enviar_mensaje(cs, error_505(ruta_absoluta))
                    with open(ruta_absoluta, 'rb') as f:
                        enviar_mensaje(cs, f.read())
                return

            if method != "GET":
                print("Error 405 Method Not Allowed")
                ruta_absoluta = webroot + "/405.html"
                if os.path.isfile(ruta_absoluta):
                    enviar_mensaje(cs, error_405(ruta_absoluta))
                    with open(ruta_absoluta, 'rb') as f:
                        enviar_mensaje(cs, f.read())
                return

            # * Leer URL y separar parámetros
            partes_url = url.split("?", 1)
            route = partes_url[0]
            parametros = partes_url[1] if len(partes_url) > 1 else None

            if parametros and "email=" in parametros:
                match = re.search(r'email=([^&]+)', parametros)
                if match:
                    correo_recibido = match.group(1)
                    if CORREO.search(correo_recibido):
                        print("Formulario: Correo válido")
                        ruta_absoluta = webroot + "/correo_valido.html"
                    else:
                        print("Formulario: Correo inválido")
                        ruta_absoluta = webroot + "/correo_invalido.html"

                    # Estructura idéntica a tus bloques de error
                    if os.path.isfile(ruta_absoluta):
                        enviar_mensaje(cs, crear_respuesta(ruta_absoluta))
                        with open(ruta_absoluta, 'rb') as f:
                            enviar_mensaje(cs, f.read())
                    else:
                        print("Faltan los archivos html del correo en el webroot")
            # * Comprobar si el recurso solicitado es /
            if route == "/":
                route = "/index.html"

            # * Construir la ruta absoluta
            ruta_absoluta = webroot + route

            # * Comprobar que el recurso existe
            if not os.path.isfile(ruta_absoluta):
                print("Error 404 Not Found:" + ruta_absoluta)
                ruta_absoluta = webroot + "/404.html"
                if os.path.isfile(ruta_absoluta):
                    enviar_mensaje(cs, error_404(ruta_absoluta))
                    with open(ruta_absoluta, 'rb') as f:
                        enviar_mensaje(cs, f.read())
                return

            # * Procesamiento de cookies SOLO si el recurso es index.html
            cookie_counter = 0
            if route == "/index.html":
                cookie_counter = process_cookies(lista_cabeceras, cs)
                if cookie_counter > MAX_ACCESOS:
                    print("Error 403 Forbidden - Maximos accesos alcanzados")
                    ruta_absoluta_403 = webroot + "/403.html"
                    if os.path.isfile(ruta_absoluta_403):
                        enviar_mensaje(cs, error_403(ruta_absoluta_403))
                        with open(ruta_absoluta_403, 'rb') as f:
                            enviar_mensaje(cs, f.read())
                    return

            # * Obtener tamaño y tipo de archivo
            length = os.stat(ruta_absoluta).st_size
            tipo_ext = route.split(".")[-1]
            content_type = filetypes.get(tipo_ext, "application/octet-stream")

            # * Enviar cabeceras de respuesta
            if route == "/index.html":
                enviar_mensaje(cs, crear_respuesta_index(ruta_absoluta, cookie_counter))
            else:
                enviar_mensaje(cs, crear_respuesta(ruta_absoluta))

            # * Enviar archivo en bloques
            with open(ruta_absoluta, 'rb') as f:
                remaining = length
                while remaining:
                    chunk_size = min(remaining, BUFSIZE)
                    buf = f.read(chunk_size)
                    if not buf:
                        break
                    enviar_mensaje(cs, buf)
                    remaining -= chunk_size
            print('\n')


def main():
    """ Función principal del servidor
    """
    try:
        # Argument parser para obtener la ip y puerto de los parámetros de ejecución del programa. IP por defecto 0.0.0.0
        parser = argparse.ArgumentParser()
        parser.add_argument("-p", "--port", help="Puerto del servidor", type=int, required=True)
        parser.add_argument("-ip", "--host", help="Dirección IP del servidor o localhost", required=True)
        parser.add_argument("-wb", "--webroot", help="Directorio base desde donde se sirven los ficheros (p.ej. /home/user/mi_web)")
        parser.add_argument('--verbose', '-v', action='store_true', help='Incluir mensajes de depuración en la salida')
        args = parser.parse_args()


        if args.verbose:
            logger.setLevel(logging.DEBUG)

        logger.info('Enabling server in address {} and port {}.'.format(args.host, args.port))

        logger.info("Serving files from {}".format(args.webroot))

        """ Funcionalidad a realizar
        """
        # Crea un socket TCP (SOCK_STREAM)
        # Permite reusar la misma dirección previamente vinculada a otro proceso. Debe ir antes de sock.bind
        #  Vinculamos el socket a una IP y puerto elegidos
        # Escucha conexiones entrantes
        server_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((args.host, args.port))
        server_socket.listen(64)

        # Bucle infinito para mantener el servidor activo indefinidamente
        # Aceptamos la conexión
        # Creamos un proceso hijo
        # Si es el proceso hijo se cierra el socket del padre y procesar la petición con process_web_request()
        # Si es el proceso padre cerrar el socket que gestiona el hijo.
        while True:
            conn, addr = server_socket.accept()
            pid = os.fork()
            if pid == 0:
                server_socket.close() #
                process_web_request(conn, args.webroot)
                cerrar_conexion(conn)
                break
            else:
                conn.close()
    except KeyboardInterrupt:
        True

if __name__== "__main__":
    main()
