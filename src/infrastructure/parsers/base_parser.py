# base_parser.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class ApiEndpoint:
    """Representa um endpoint de API encontrado"""
    path: str
    method: str
    handler: str
    parameters: List[Dict[str, str]]
    file_path: str
    line_number: int
    auth_required: Optional[bool] = None
    pii_fields: List[str] = None
    
    def to_dict(self):
        return asdict(self)


class BaseParser(ABC):
    """Classe base abstrata para parsers de diferentes linguagens"""
    
    def __init__(self, language_name: str):
        self.language_name = language_name
        self.supported_extensions: set = set()
        self.ignore_suffixes: set = set()
    
    @abstractmethod
    def extract_api_endpoints(self, code: str, file_path: str = "unknown") -> List[Dict]:
        """Extrai endpoints de API do código fonte"""
        pass
    
    @abstractmethod
    def get_ast_summary(self, code: str) -> Dict[str, Any]:
        """Retorna um resumo da AST para análise"""
        pass
    
    def supports_file(self, file_path: str) -> bool:
        """Verifica se o parser suporta o arquivo"""
        import os
        ext = os.path.splitext(file_path)[1]
        if ext not in self.supported_extensions:
            return False
        
        # Verifica se deve ignorar por sufixo
        for suffix in self.ignore_suffixes:
            if file_path.endswith(suffix):
                return False
        
        return True