"""
Modelos SQLAlchemy y funciones de acceso a datos.
Base de datos SQLite con WAL para concurrencia lectura/escritura.
"""
import json
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime,
    ForeignKey, event, Index
)
from sqlalchemy.orm import (
    declarative_base, sessionmaker, scoped_session, relationship
)

from config import DATABASE_URL

# ─── Engine con WAL mode para concurrencia ────────────────────────────
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
    echo=False,
)

@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()

SessionFactory = sessionmaker(bind=engine)
ScopedSession = scoped_session(SessionFactory)

Base = declarative_base()


# ═══════════════════════════════════════════════════════════════════════
# MODELOS
# ═══════════════════════════════════════════════════════════════════════

class Lote(Base):
    """Representa un lote de DNIs subidos por el usuario."""
    __tablename__ = "lotes"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    nombre_archivo = Column(String(255), nullable=False)
    total_dnis     = Column(Integer, default=0)
    created_at     = Column(DateTime, default=datetime.utcnow)

    registros = relationship("Registro", back_populates="lote", lazy="dynamic")

    def __repr__(self):
        return f"<Lote {self.id} '{self.nombre_archivo}' ({self.total_dnis} DNIs)>"


class Registro(Base):
    """Un DNI individual con su estado en el pipeline."""
    __tablename__ = "registros"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    lote_id          = Column(Integer, ForeignKey("lotes.id"), nullable=False)
    dni              = Column(String(15), nullable=False, index=True)
    estado           = Column(String(30), nullable=False, default="PENDIENTE", index=True)
    retry_count      = Column(Integer, default=0)    # Cuántas veces se ha reintentado
    payload_sunedu   = Column(Text, default=None)   # JSON serializado
    payload_minedu   = Column(Text, default=None)   # JSON serializado
    error_msg        = Column(Text, default=None)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lote = relationship("Lote", back_populates="registros")

    # ── Helpers para payload JSON ──
    def set_payload_sunedu(self, data: dict):
        self.payload_sunedu = json.dumps(data, ensure_ascii=False)

    def set_payload_minedu(self, data: dict):
        self.payload_minedu = json.dumps(data, ensure_ascii=False)

    def get_payload_sunedu(self) -> Optional[dict]:
        return json.loads(self.payload_sunedu) if self.payload_sunedu else None

    def get_payload_minedu(self) -> Optional[dict]:
        return json.loads(self.payload_minedu) if self.payload_minedu else None

    def __repr__(self):
        return f"<Registro DNI={self.dni} estado={self.estado}>"


# Índice compuesto para queries del worker
Index("ix_registros_estado_id", Registro.estado, Registro.id)


# ═══════════════════════════════════════════════════════════════════════
# CREAR TABLAS
# ═══════════════════════════════════════════════════════════════════════

def init_db():
    """Crea todas las tablas si no existen."""
    Base.metadata.create_all(engine)


# ═══════════════════════════════════════════════════════════════════════
# FUNCIONES CRUD
# ═══════════════════════════════════════════════════════════════════════

def crear_lote(nombre_archivo: str, dnis: List[str]) -> Lote:
    """Crea un lote con sus registros. Deduplica DNIs dentro del lote."""
    session = SessionFactory()
    try:
        # Deduplicar conservando orden
        vistos = set()
        dnis_unicos = []
        for d in dnis:
            d_clean = d.strip()
            if d_clean and d_clean not in vistos:
                vistos.add(d_clean)
                dnis_unicos.append(d_clean)

        lote = Lote(nombre_archivo=nombre_archivo, total_dnis=len(dnis_unicos))
        session.add(lote)
        session.flush()  # Para obtener lote.id

        for dni in dnis_unicos:
            reg = Registro(lote_id=lote.id, dni=dni, estado="PENDIENTE")
            session.add(reg)

        session.commit()
        session.refresh(lote)
        return lote
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def tomar_siguiente(estado_origen: str, estado_procesando: str) -> Optional[Registro]:
    """
    Toma atómicamente el siguiente registro en `estado_origen`,
    lo marca como `estado_procesando` y lo retorna.
    Retorna None si no hay trabajo.
    """
    session = SessionFactory()
    try:
        reg = (
            session.query(Registro)
            .filter(Registro.estado == estado_origen)
            .order_by(Registro.id.asc())
            .with_for_update()
            .first()
        )
        if reg is None:
            return None

        reg.estado = estado_procesando
        reg.updated_at = datetime.utcnow()
        session.commit()

        # Retornar datos desacoplados de la sesión
        data = {
            "id": reg.id,
            "dni": reg.dni,
            "lote_id": reg.lote_id,
            "retry_count": reg.retry_count or 0,
        }
        return type("RegistroDTO", (), data)()
    except Exception:
        session.rollback()
        return None
    finally:
        session.close()


def actualizar_resultado(
    registro_id: int,
    nuevo_estado: str,
    payload_sunedu: Optional[dict] = None,
    payload_minedu: Optional[dict] = None,
    error_msg: Optional[str] = None,
):
    """Actualiza el estado y payload de un registro."""
    session = SessionFactory()
    try:
        reg = session.query(Registro).filter(Registro.id == registro_id).first()
        if reg is None:
            return

        reg.estado = nuevo_estado
        reg.updated_at = datetime.utcnow()

        if payload_sunedu is not None:
            reg.set_payload_sunedu(payload_sunedu)
        if payload_minedu is not None:
            reg.set_payload_minedu(payload_minedu)
        if error_msg is not None:
            reg.error_msg = error_msg

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def obtener_conteos() -> Dict[str, int]:
    """Retorna conteo de registros por estado."""
    session = SessionFactory()
    try:
        from sqlalchemy import func
        rows = (
            session.query(Registro.estado, func.count(Registro.id))
            .group_by(Registro.estado)
            .all()
        )
        return {estado: count for estado, count in rows}
    finally:
        session.close()


def obtener_total() -> int:
    """Total de registros en la BD."""
    session = SessionFactory()
    try:
        return session.query(Registro).count()
    finally:
        session.close()


def obtener_registros(
    estado: Optional[str] = None,
    lote_id: Optional[int] = None,
    limit: int = 500,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Retorna registros como lista de dicts."""
    session = SessionFactory()
    try:
        q = session.query(Registro)
        if estado:
            q = q.filter(Registro.estado == estado)
        if lote_id:
            q = q.filter(Registro.lote_id == lote_id)
        q = q.order_by(Registro.id.asc()).offset(offset).limit(limit)

        resultados = []
        for r in q.all():
            d = {
                "id": r.id,
                "lote_id": r.lote_id,
                "dni": r.dni,
                "estado": r.estado,
                "retry_count": r.retry_count or 0,
                "error_msg": r.error_msg,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            # Expandir payloads
            ps = r.get_payload_sunedu()
            if ps:
                d["sunedu_nombres"] = ps.get("nombres", "")
                d["sunedu_grado"] = ps.get("grado_o_titulo", "")
                d["sunedu_institucion"] = ps.get("institucion", "")
                d["sunedu_fecha_diploma"] = ps.get("fecha_diploma", "")
            pm = r.get_payload_minedu()
            if pm:
                d["minedu_nombres"] = pm.get("nombre_completo", "")
                d["minedu_titulo"] = pm.get("titulo", "")
                d["minedu_institucion"] = pm.get("institucion", "")
                d["minedu_fecha"] = pm.get("fecha_expedicion", "")
            resultados.append(d)
        return resultados
    finally:
        session.close()


def obtener_lotes() -> List[Dict[str, Any]]:
    """Lista todos los lotes."""
    session = SessionFactory()
    try:
        lotes = session.query(Lote).order_by(Lote.id.desc()).all()
        return [
            {
                "id": l.id,
                "nombre_archivo": l.nombre_archivo,
                "total_dnis": l.total_dnis,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in lotes
        ]
    finally:
        session.close()


def reintentar_no_encontrados() -> Dict[str, Any]:
    """
    Re-encola TODOS los registros NOT_FOUND y ERROR_* de vuelta a PENDIENTE
    para que pasen otra vez por SUNEDU → MINEDU (una sola pasada).
    Sin límite de reintentos — el usuario controla cuántas veces pulsa el botón.
    """
    from config import Estado
    session = SessionFactory()
    try:
        estados_retry = [Estado.NOT_FOUND, Estado.ERROR_SUNEDU, Estado.ERROR_MINEDU]
        registros = (
            session.query(Registro)
            .filter(Registro.estado.in_(estados_retry))
            .all()
        )
        reencolados = 0
        for reg in registros:
            reg.estado = Estado.PENDIENTE
            reg.retry_count = (reg.retry_count or 0) + 1
            reg.error_msg = None
            reg.payload_sunedu = None
            reg.payload_minedu = None
            reg.updated_at = datetime.utcnow()
            reencolados += 1
        session.commit()
        return {"reencolados": reencolados}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def hay_trabajo_pendiente() -> bool:
    """Retorna True si hay registros en estados no-terminales."""
    from config import Estado
    session = SessionFactory()
    try:
        estados_activos = [
            Estado.PENDIENTE, Estado.PROCESANDO_SUNEDU,
            Estado.CHECK_MINEDU, Estado.PROCESANDO_MINEDU,
        ]
        count = (
            session.query(Registro)
            .filter(Registro.estado.in_(estados_activos))
            .count()
        )
        return count > 0
    finally:
        session.close()


def contar_retryables() -> int:
    """Retorna la cantidad de registros NOT_FOUND / ERROR que se pueden reintentar."""
    from config import Estado
    session = SessionFactory()
    try:
        estados_retry = [Estado.NOT_FOUND, Estado.ERROR_SUNEDU, Estado.ERROR_MINEDU]
        return (
            session.query(Registro)
            .filter(Registro.estado.in_(estados_retry))
            .count()
        )
    finally:
        session.close()


def recuperar_procesando() -> Dict[str, int]:
    """
    Recupera registros atrapados en estados PROCESANDO_*
    (por ejemplo, si un worker murió o fue detenido bruscamente).
    PROCESANDO_SUNEDU → PENDIENTE
    PROCESANDO_MINEDU → CHECK_MINEDU
    """
    from config import Estado
    session = SessionFactory()
    try:
        sunedu = (
            session.query(Registro)
            .filter(Registro.estado == Estado.PROCESANDO_SUNEDU)
            .all()
        )
        for r in sunedu:
            r.estado = Estado.PENDIENTE
            r.updated_at = datetime.utcnow()

        minedu = (
            session.query(Registro)
            .filter(Registro.estado == Estado.PROCESANDO_MINEDU)
            .all()
        )
        for r in minedu:
            r.estado = Estado.CHECK_MINEDU
            r.updated_at = datetime.utcnow()

        session.commit()
        return {"sunedu_recuperados": len(sunedu), "minedu_recuperados": len(minedu)}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def limpiar_todo() -> Dict[str, int]:
    """Elimina todos los registros y lotes de la base de datos."""
    session = SessionFactory()
    try:
        registros_eliminados = session.query(Registro).delete()
        lotes_eliminados = session.query(Lote).delete()
        session.commit()
        return {
            "registros_eliminados": registros_eliminados,
            "lotes_eliminados": lotes_eliminados,
        }
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# Inicializar BD al importar
init_db()
