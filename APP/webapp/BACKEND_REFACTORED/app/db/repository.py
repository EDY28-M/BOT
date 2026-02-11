
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import func
from app.db.session import SessionFactory
from app.db.models import Lote, Registro
from app.core.config import Estado

class DniRepository:
    def __init__(self):
        self.session_factory = SessionFactory

    def crear_lote(self, nombre_archivo: str, dnis: List[str]) -> Lote:
        """Crea un lote con sus registros. Deduplica DNIs dentro del lote."""
        session = self.session_factory()
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
                reg = Registro(lote_id=lote.id, dni=dni, estado=Estado.PENDIENTE)
                session.add(reg)

            session.commit()
            session.refresh(lote)
            return lote
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def tomar_siguiente(self, estado_origen: str, estado_procesando: str) -> Optional[Dict[str, Any]]:
        """
        Toma atómicamente el siguiente registro en `estado_origen`,
        lo marca como `estado_procesando` y lo retorna como dict.
        """
        session = self.session_factory()
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

            return {
                "id": reg.id,
                "dni": reg.dni,
                "lote_id": reg.lote_id,
                "retry_count": reg.retry_count or 0,
            }
        except Exception:
            session.rollback()
            return None
        finally:
            session.close()

    def actualizar_resultado(
        self,
        registro_id: int,
        nuevo_estado: str,
        payload_sunedu: Optional[dict] = None,
        payload_minedu: Optional[dict] = None,
        error_msg: Optional[str] = None,
    ):
        """Actualiza el estado y payload de un registro."""
        session = self.session_factory()
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

    def obtener_conteos(self) -> Dict[str, int]:
        """Retorna conteo de registros por estado."""
        session = self.session_factory()
        try:
            rows = (
                session.query(Registro.estado, func.count(Registro.id))
                .group_by(Registro.estado)
                .all()
            )
            return {estado: count for estado, count in rows}
        finally:
            session.close()

    def obtener_total(self) -> int:
        session = self.session_factory()
        try:
            return session.query(Registro).count()
        finally:
            session.close()

    def obtener_registros(
        self,
        estado: Optional[str] = None,
        lote_id: Optional[int] = None,
        limit: int = 500,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        session = self.session_factory()
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
                ps = r.get_payload_sunedu()
                if ps:
                    if isinstance(ps, list) and len(ps) > 0:
                        ps = ps[0]
                    if isinstance(ps, dict):
                        d["sunedu_nombres"] = ps.get("nombres", "")
                        d["sunedu_grado"] = ps.get("grado_o_titulo", "")
                        d["sunedu_institucion"] = ps.get("institucion", "")
                        d["sunedu_fecha_diploma"] = ps.get("fecha_diploma", "")

                pm = r.get_payload_minedu()
                if pm:
                    if isinstance(pm, list) and len(pm) > 0:
                        pm = pm[0]
                    if isinstance(pm, dict):
                        d["minedu_nombres"] = pm.get("nombre_completo", "")
                        d["minedu_titulo"] = pm.get("titulo", "")
                        d["minedu_institucion"] = pm.get("institucion", "")
                        d["minedu_fecha"] = pm.get("fecha_expedicion", "")
                resultados.append(d)
            return resultados
        finally:
            session.close()

    def obtener_lotes(self) -> List[Dict[str, Any]]:
        session = self.session_factory()
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

    def reintentar_no_encontrados(self) -> Dict[str, Any]:
        """Re-encola NOT_FOUND y ERROR_*."""
        session = self.session_factory()
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

    def hay_trabajo_pendiente(self) -> bool:
        session = self.session_factory()
        try:
            estados_activos = [
                Estado.PENDIENTE, Estado.PROCESANDO_SUNEDU,
                Estado.CHECK_MINEDU, Estado.PROCESANDO_MINEDU,
            ]
            count = session.query(Registro).filter(Registro.estado.in_(estados_activos)).count()
            return count > 0
        finally:
            session.close()

    def contar_retryables(self) -> int:
        session = self.session_factory()
        try:
            estados_retry = [Estado.NOT_FOUND, Estado.ERROR_SUNEDU, Estado.ERROR_MINEDU]
            return session.query(Registro).filter(Registro.estado.in_(estados_retry)).count()
        finally:
            session.close()

    def recuperar_procesando(self) -> Dict[str, int]:
        """Recupera registros atrapados en estados PROCESANDO_*."""
        session = self.session_factory()
        try:
            sunedu = session.query(Registro).filter(Registro.estado == Estado.PROCESANDO_SUNEDU).all()
            for r in sunedu:
                r.estado = Estado.PENDIENTE
                r.updated_at = datetime.utcnow()

            minedu = session.query(Registro).filter(Registro.estado == Estado.PROCESANDO_MINEDU).all()
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

    def limpiar_todo(self) -> Dict[str, int]:
        session = self.session_factory()
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
