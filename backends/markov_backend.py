from typing import Optional, Pattern

class MarkovBackend:
    def record_and_generate(self, input_string:str, split_pattern: Pattern, word_limit: int) -> Optional[str]:
        raise NotImplementedError