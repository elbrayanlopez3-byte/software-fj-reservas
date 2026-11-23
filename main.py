from abc import ABC, abstractmethod
from datetime import datetime
from functools import singledispatchmethod
from pathlib import Path
import re


# ==========================================
# 1. EXCEPCIONES PERSONALIZADAS
# ==========================================
class ErrorSistemaSoftwareFJ(Exception):
    def __init__(self, mensaje, codigo="ERR_GENERAL"):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


class ErrorValidacionDatos(ErrorSistemaSoftwareFJ):
    def __init__(self, mensaje, campo=None):
        super().__init__(mensaje, codigo="ERR_VALIDACION")
        self.campo = campo


class ErrorDisponibilidadServicio(ErrorSistemaSoftwareFJ):
    def __init__(self, mensaje, id_servicio=None):
        super().__init__(mensaje, codigo="ERR_DISPONIBILIDAD")
        self.id_servicio = id_servicio


class ErrorOperacionReserva(ErrorSistemaSoftwareFJ):
    def __init__(self, mensaje, id_reserva=None):
        super().__init__(mensaje, codigo="ERR_RESERVA")
        self.id_reserva = id_reserva


class ErrorCalculoFinanciero(ErrorSistemaSoftwareFJ):
    def __init__(self, mensaje):
        super().__init__(mensaje, codigo="ERR_CALCULO")


# ==========================================
# 2. REGISTRO DE LOGS EN ARCHIVO (SIN BD)
# ==========================================
class RegistradorLog:
    def __init__(self, ruta_log="logs/sistema_software_fj.log"):
        self.ruta = Path(ruta_log)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)

    def registrar(self, nivel, mensaje):
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        linea = f"[{fecha}] [{nivel}] {mensaje}\n"
        with self.ruta.open("a", encoding="utf-8") as archivo:
            archivo.write(linea)


# ==========================================
# 3. CLASE ABSTRACTA GENERAL Y CLIENTE
# ==========================================
class EntidadSistema(ABC):
    def __init__(self, id_entidad, nombre):
        if not id_entidad or not str(id_entidad).strip():
            raise ErrorValidacionDatos("El ID no puede estar vacío.", campo="id_entidad")
        if not nombre or not str(nombre).strip():
            raise ErrorValidacionDatos("El nombre no puede estar vacío.", campo="nombre")

        self._id_entidad = str(id_entidad).strip()
        self._nombre = str(nombre).strip()

    @property
    def id_entidad(self):
        return self._id_entidad

    @property
    def nombre(self):
        return self._nombre

    @nombre.setter
    def nombre(self, valor):
        if not valor or len(str(valor).strip()) < 2:
            raise ErrorValidacionDatos("El nombre debe tener al menos 2 caracteres.", campo="nombre")
        self._nombre = str(valor).strip()

    @abstractmethod
    def resumen(self):
        pass


class Cliente(EntidadSistema):
    _PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    def __init__(self, id_entidad, nombre, correo, telefono, activo=True):
        super().__init__(id_entidad, nombre)
        self._correo = ""
        self._telefono = ""
        self._activo = bool(activo)
        self.correo = correo
        self.telefono = telefono

    @property
    def correo(self):
        return self._correo

    @correo.setter
    def correo(self, valor):
        if not valor or not self._PATRON_CORREO.match(str(valor).strip()):
            raise ErrorValidacionDatos(f"Correo inválido: '{valor}'", campo="correo")
        self._correo = str(valor).strip().lower()

    @property
    def telefono(self):
        return self._telefono

    @telefono.setter
    def telefono(self, valor):
        numeros = re.sub(r"[\s\-()]", "", str(valor or ""))
        if not numeros.isdigit() or not (7 <= len(numeros) <= 15):
            raise ErrorValidacionDatos(f"Teléfono inválido: '{valor}'", campo="telefono")
        self._telefono = numeros

    @property
    def activo(self):
        return self._activo

    def resumen(self):
        estado = "Activo" if self._activo else "Inactivo"
        return f"Cliente [{self._id_entidad}] {self._nombre} | {self._correo} | Tel: {self._telefono} | {estado}"


# ==========================================
# 4. SERVICIO ABSTRACTO Y 3 SERVICIOS
# ==========================================
class Servicio(ABC):
    def __init__(self, id_servicio, nombre, tarifa_base, disponible=True):
        if not id_servicio or not str(id_servicio).strip():
            raise ErrorValidacionDatos("El ID del servicio es obligatorio.", campo="id_servicio")
        if not nombre or not str(nombre).strip():
            raise ErrorValidacionDatos("El nombre del servicio es obligatorio.", campo="nombre")
        if tarifa_base is None or tarifa_base <= 0:
            raise ErrorCalculoFinanciero("La tarifa base debe ser mayor que cero.")

        self._id_servicio = str(id_servicio).strip()
        self._nombre = str(nombre).strip()
        self._tarifa_base = float(tarifa_base)
        self._disponible = bool(disponible)

    @property
    def id_servicio(self):
        return self._id_servicio

    @property
    def nombre(self):
        return self._nombre

    @property
    def disponible(self):
        return self._disponible

    def verificar_disponibilidad(self):
        if not self._disponible:
            raise ErrorDisponibilidadServicio(
                f"El servicio '{self._nombre}' no está disponible.",
                id_servicio=self._id_servicio,
            )

    def marcar_no_disponible(self):
        self._disponible = False

    def marcar_disponible(self):
        self._disponible = True

    def _subtotal_horas(self, horas):
        if horas is None or horas <= 0:
            raise ErrorCalculoFinanciero("Las horas deben ser mayores que cero.")
        return self._tarifa_base * float(horas)

    def _aplicar_descuento_e_impuesto(self, subtotal, descuento_pct=0.0, impuesto_pct=0.19):
        if subtotal < 0:
            raise ErrorCalculoFinanciero("El subtotal no puede ser negativo.")
        if descuento_pct < 0 or descuento_pct >= 100:
            raise ErrorCalculoFinanciero(f"Descuento inválido: {descuento_pct}%")
        if impuesto_pct < 0:
            raise ErrorCalculoFinanciero(f"Impuesto inválido: {impuesto_pct}%")

        con_descuento = subtotal * (1 - descuento_pct / 100.0)
        total = con_descuento * (1 + impuesto_pct / 100.0)
        return round(total, 2)

    # Método sobrecargado según tipo de dato (int, float o dict)
    @singledispatchmethod
    def calcular_costo_sobrecargado(self, dato, descuento_pct=0.0, impuesto_pct=0.19):
        raise ErrorValidacionDatos(f"Tipo no soportado: {type(dato).__name__}", campo="dato")

    @calcular_costo_sobrecargado.register
    def _(self, horas: int, descuento_pct=0.0, impuesto_pct=0.19):
        return self._aplicar_descuento_e_impuesto(self._subtotal_horas(horas), descuento_pct, impuesto_pct)

    @calcular_costo_sobrecargado.register
    def _(self, horas: float, descuento_pct=0.0, impuesto_pct=0.19):
        return self._aplicar_descuento_e_impuesto(self._subtotal_horas(horas), descuento_pct, impuesto_pct)

    @calcular_costo_sobrecargado.register
    def _(self, datos: dict, descuento_pct=0.0, impuesto_pct=0.19):
        if "horas" not in datos:
            raise ErrorValidacionDatos("Falta la clave 'horas' en el diccionario.", campo="horas")
        return self._aplicar_descuento_e_impuesto(self._subtotal_horas(datos["horas"]), descuento_pct, impuesto_pct)

    @abstractmethod
    def validar_parametros(self, horas, **kwargs):
        pass

    @abstractmethod
    def describir_servicio(self):
        pass

    @abstractmethod
    def calcular_costo(self, horas, descuento_pct=0.0, impuesto_pct=0.19, **kwargs):
        pass


class ReservaSala(Servicio):
    def __init__(self, id_servicio, nombre, tarifa_base, capacidad, disponible=True):
        super().__init__(id_servicio, nombre, tarifa_base, disponible)
        if capacidad <= 0:
            raise ErrorValidacionDatos("La capacidad debe ser mayor que cero.", campo="capacidad")
        self.capacidad = capacidad

    def validar_parametros(self, horas, **kwargs):
        self._subtotal_horas(horas)
        asistentes = kwargs.get("asistentes", 1)
        if not isinstance(asistentes, int) or asistentes <= 0:
            raise ErrorValidacionDatos("Asistentes debe ser entero positivo.", campo="asistentes")
        if asistentes > self.capacidad:
            raise ErrorValidacionDatos(
                f"Asistentes ({asistentes}) superan capacidad ({self.capacidad}).",
                campo="asistentes",
            )

    def describir_servicio(self):
        return f"Sala [{self._id_servicio}] {self._nombre} | Cap: {self.capacidad} | Tarifa/h: ${self._tarifa_base:,.2f}"

    def calcular_costo(self, horas, descuento_pct=0.0, impuesto_pct=0.19, **kwargs):
        self.validar_parametros(horas, **kwargs)
        limpieza = float(kwargs.get("limpieza", 0.0))
        if limpieza < 0:
            raise ErrorCalculoFinanciero("El recargo de limpieza no puede ser negativo.")
        subtotal = self._subtotal_horas(horas) + limpieza
        return self._aplicar_descuento_e_impuesto(subtotal, descuento_pct, impuesto_pct)


class AlquilerEquipo(Servicio):
    def __init__(self, id_servicio, nombre, tarifa_base, unidades, disponible=True):
        super().__init__(id_servicio, nombre, tarifa_base, disponible)
        if unidades <= 0:
            raise ErrorValidacionDatos("Las unidades deben ser mayores que cero.", campo="unidades")
        self.unidades = unidades

    def validar_parametros(self, horas, **kwargs):
        self._subtotal_horas(horas)
        cantidad = kwargs.get("cantidad", 1)
        if not isinstance(cantidad, int) or cantidad <= 0:
            raise ErrorValidacionDatos("Cantidad debe ser entero positivo.", campo="cantidad")
        if cantidad > self.unidades:
            raise ErrorDisponibilidadServicio(
                f"Piden {cantidad} equipos y solo hay {self.unidades}.",
                id_servicio=self._id_servicio,
            )

    def describir_servicio(self):
        return f"Equipo [{self._id_servicio}] {self._nombre} | Unidades: {self.unidades} | Tarifa/h: ${self._tarifa_base:,.2f}"

    def calcular_costo(self, horas, descuento_pct=0.0, impuesto_pct=0.19, **kwargs):
        self.validar_parametros(horas, **kwargs)
        cantidad = int(kwargs.get("cantidad", 1))
        subtotal = self._subtotal_horas(horas) * cantidad
        return self._aplicar_descuento_e_impuesto(subtotal, descuento_pct, impuesto_pct)


class AsesoriaEspecializada(Servicio):
    def __init__(self, id_servicio, nombre, tarifa_base, especialidad, disponible=True):
        super().__init__(id_servicio, nombre, tarifa_base, disponible)
        if not especialidad or not str(especialidad).strip():
            raise ErrorValidacionDatos("La especialidad es obligatoria.", campo="especialidad")
        self.especialidad = str(especialidad).strip()

    def validar_parametros(self, horas, **kwargs):
        self._subtotal_horas(horas)
        if horas < 1:
            raise ErrorValidacionDatos("La asesoría requiere mínimo 1 hora.", campo="horas")

    def describir_servicio(self):
        return f"Asesoría [{self._id_servicio}] {self._nombre} ({self.especialidad}) | Tarifa/h: ${self._tarifa_base:,.2f}"

    def calcular_costo(self, horas, descuento_pct=0.0, impuesto_pct=0.19, **kwargs):
        self.validar_parametros(horas, **kwargs)
        subtotal = self._subtotal_horas(horas)
        return self._aplicar_descuento_e_impuesto(subtotal, descuento_pct, impuesto_pct)


# ==========================================
# 5. RESERVA Y GESTOR EN MEMORIA
# ==========================================
class Reserva:
    def __init__(self, id_reserva, cliente, servicio, horas, descuento_pct=0.0, impuesto_pct=0.19, **kwargs):
        if not id_reserva or not str(id_reserva).strip():
            raise ErrorValidacionDatos("El ID de reserva es obligatorio.", campo="id_reserva")
        if not isinstance(cliente, Cliente):
            raise ErrorValidacionDatos("Cliente no válido.", campo="cliente")
        if not cliente.activo:
            raise ErrorOperacionReserva("El cliente está inactivo.", id_reserva=id_reserva)
        if not isinstance(servicio, Servicio):
            raise ErrorValidacionDatos("Servicio no válido.", campo="servicio")

        servicio.verificar_disponibilidad()
        servicio.validar_parametros(horas, **kwargs)

        self.id_reserva = str(id_reserva).strip()
        self.cliente = cliente
        self.servicio = servicio
        self.horas = float(horas)
        self.descuento_pct = float(descuento_pct)
        self.impuesto_pct = float(impuesto_pct)
        self.kwargs = kwargs
        self.estado = "PENDIENTE"
        self.total = self._calcular_total_seguro()

    def _calcular_total_seguro(self):
        try:
            return self.servicio.calcular_costo(
                self.horas,
                descuento_pct=self.descuento_pct,
                impuesto_pct=self.impuesto_pct,
                **self.kwargs,
            )
        except ErrorSistemaSoftwareFJ as exc:
            # Encadenamiento de excepciones
            raise ErrorCalculoFinanciero(
                f"Error al calcular total de la reserva '{self.id_reserva}': {exc}"
            ) from exc

    def confirmar(self):
        if self.estado == "CANCELADA":
            raise ErrorOperacionReserva("No se puede confirmar una reserva cancelada.", id_reserva=self.id_reserva)
        if self.estado == "CONFIRMADA":
            raise ErrorOperacionReserva("La reserva ya está confirmada.", id_reserva=self.id_reserva)
        self.servicio.verificar_disponibilidad()
        self.servicio.marcar_no_disponible()
        self.estado = "CONFIRMADA"

    def cancelar(self):
        if self.estado == "CANCELADA":
            raise ErrorOperacionReserva("La reserva ya estaba cancelada.", id_reserva=self.id_reserva)
        self.estado = "CANCELADA"
        self.servicio.marcar_disponible()

    def resumen(self):
        return f"Reserva [{self.id_reserva}] | {self.estado} | Cliente: {self.cliente.nombre} | Servicio: {self.servicio.nombre} | Total: ${self.total:,.2f}"


class GestorSoftwareFJ:
    def __init__(self, ruta_log="logs/sistema_software_fj.log"):
        self.clientes = []
        self.servicios = []
        self.reservas = []
        self.logger = RegistradorLog(ruta_log)

    def registrar_cliente(self, cliente):
        self.clientes.append(cliente)
        self.logger.registrar("INFO", f"Cliente registrado: {cliente.resumen()}")

    def registrar_servicio(self, servicio):
        self.servicios.append(servicio)
        self.logger.registrar("INFO", f"Servicio registrado: {servicio.describir_servicio()}")

    def procesar_reserva(self, reserva, confirmar=True):
        resultado = "INICIADA"
        try:
            if confirmar:
                reserva.confirmar()
            self.reservas.append(reserva)
        except ErrorSistemaSoftwareFJ as exc:
            resultado = "FALLIDA"
            self.logger.registrar("ERROR", f"[{exc.codigo}] {exc}")
            raise
        else:
            resultado = "EXITOSA"
            self.logger.registrar("INFO", f"Reserva creada: {reserva.resumen()}")
            return reserva
        finally:
            self.logger.registrar("AUDIT", f"Intento reserva '{reserva.id_reserva}' -> {resultado}")


# ==========================================
# 6. SIMULACIÓN DE 11 OPERACIONES
# ==========================================
def main():
    gestor = GestorSoftwareFJ()
    print("--- INICIO SIMULACIÓN SOFTWARE FJ ---\n")

    # 1. Cliente válido 1
    try:
        c1 = Cliente("C1", "Ana Torres", "ana@correo.com", "3001112233")
        gestor.registrar_cliente(c1)
        print("1. OK:", c1.resumen())
    except ErrorSistemaSoftwareFJ as e:
        gestor.logger.registrar("ERROR", str(e))
        print("1. ERROR:", e)

    # 2. Cliente inválido (correo malo)
    try:
        c_malo = Cliente("C2", "Pedro", "correo_malo", "3001112233")
        gestor.registrar_cliente(c_malo)
    except ErrorSistemaSoftwareFJ as e:
        gestor.logger.registrar("ERROR", f"Op 2 rechazada: {e}")
        print("2. ERROR CONTROLADO:", e)

    # 3. Cliente válido 2
    try:
        c2 = Cliente("C3", "Luis Díaz", "luis@empresa.co", "3114445566")
        gestor.registrar_cliente(c2)
        print("3. OK:", c2.resumen())
    except ErrorSistemaSoftwareFJ as e:
        gestor.logger.registrar("ERROR", str(e))
        print("3. ERROR:", e)

    # 4. Crear los 3 servicios válidos
    try:
        sala = ReservaSala("S1", "Sala Reuniones 1", 60000, capacidad=10)
        equipo = AlquilerEquipo("S2", "Portátiles", 20000, unidades=5)
        asesoria = AsesoriaEspecializada("S3", "Soporte Python", 100000, especialidad="Backend")
        gestor.registrar_servicio(sala)
        gestor.registrar_servicio(equipo)
        gestor.registrar_servicio(asesoria)
        print("4. OK: 3 servicios creados.")
    except ErrorSistemaSoftwareFJ as e:
        gestor.logger.registrar("ERROR", str(e))
        print("4. ERROR:", e)

    # 5. Crear servicio inválido (tarifa 0)
    try:
        s_malo = ReservaSala("S4", "Sala Rota", 0, capacidad=5)
        gestor.registrar_servicio(s_malo)
    except ErrorSistemaSoftwareFJ as e:
        gestor.logger.registrar("ERROR", f"Op 5 rechazada: {e}")
        print("5. ERROR CONTROLADO:", e)

    # 6. Probar método sobrecargado
    try:
        v1 = asesoria.calcular_costo_sobrecargado(2)
        v2 = asesoria.calcular_costo_sobrecargado(1.5, descuento_pct=10)
        v3 = asesoria.calcular_costo_sobrecargado({"horas": 3})
        gestor.logger.registrar("INFO", f"Sobrecarga OK -> int={v1}, float={v2}, dict={v3}")
        print(f"6. OK Sobrecarga: int={v1}, float={v2}, dict={v3}")
    except ErrorSistemaSoftwareFJ as e:
        gestor.logger.registrar("ERROR", str(e))
        print("6. ERROR:", e)

    # 7. Reserva exitosa de sala
    r1 = None
    try:
        r1 = Reserva("R1", c1, sala, horas=3, asistentes=6, limpieza=15000)
        gestor.procesar_reserva(r1, confirmar=True)
        print("7. OK:", r1.resumen())
    except ErrorSistemaSoftwareFJ as e:
        print("7. ERROR:", e)

    # 8. Reserva fallida por sala ya ocupada
    try:
        r2 = Reserva("R2", c2, sala, horas=2, asistentes=4)
        gestor.procesar_reserva(r2, confirmar=True)
    except ErrorSistemaSoftwareFJ as e:
        print("8. ERROR CONTROLADO:", e)

    # 9. Reserva exitosa de equipos
    try:
        r3 = Reserva("R3", c2, equipo, horas=4, descuento_pct=5, cantidad=2)
        gestor.procesar_reserva(r3, confirmar=True)
        print("9. OK:", r3.resumen())
    except ErrorSistemaSoftwareFJ as e:
        print("9. ERROR:", e)

    # 10. Reserva fallida con excepción encadenada (descuento > 100)
    try:
        r4 = Reserva("R4", c1, asesoria, horas=2, descuento_pct=150)
        gestor.procesar_reserva(r4, confirmar=True)
    except ErrorSistemaSoftwareFJ as e:
        gestor.logger.registrar("ERROR", f"Op 10 encadenada: {e} | Causa: {e.__cause__}")
        print("10. ERROR ENCADENADO:", e, "| Causa:", e.__cause__)

    # 11. Cancelar reserva y probar error al reconfirmar cancelada
    if r1 is not None:
        try:
            r1.cancelar()
            gestor.logger.registrar("INFO", f"Reserva {r1.id_reserva} cancelada.")
            print("11a. OK Cancelada:", r1.resumen())
            r1.confirmar()
        except ErrorSistemaSoftwareFJ as e:
            gestor.logger.registrar("ERROR", f"Op 11b rechazada: {e}")
            print("11b. ERROR CONTROLADO:", e)

    print("\n--- FIN DE LA SIMULACIÓN (SIN CAÍDAS) ---")


if __name__ == "__main__":
    main()