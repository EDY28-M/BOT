
import json
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db.session import Base

class Lote(Base):
    """Representa un lote de DNIs subidos por el usuario."""
    __tablename__ = "lotes"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    nombre_archivo = Column(String(255), nullable=False)
    total_dnis     = Column(Integer, default=0)
    created_at     = Column(DateTime, default=datetime.utcnow)

    registros = relationship("Registro", back_populates="lote", lazy="dynamic")

    def __repr__(self):
        return f"<Lote {self.id} '{self.nombre_archivo}'>"


class Registro(Base):
    """Un DNI individual con su estado en el pipeline."""
    __tablename__ = "registros"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    lote_id          = Column(Integer, ForeignKey("lotes.id"), nullable=False)
    dni              = Column(String(15), nullable=False, index=True)
    estado           = Column(String(30), nullable=False, default="PENDIENTE", index=True)
    retry_count      = Column(Integer, default=0)    
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


# Índice compuesto para optimizar la búsqueda de pendientes
Index("ix_registros_estado_id", Registro.estado, Registro.id)
