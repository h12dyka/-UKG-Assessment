from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        Mengurai berkas fisik dan mengembalikan dictionary standar:
        {
            'success': bool,
            'summary': str,
            'extracted_content': str,
            'metadata': dict,
            'error': Optional[str]
        }
        """
        pass
