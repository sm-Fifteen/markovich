from typing import Optional, Pattern, List

class MarkovBackend:
    async def record_and_generate(self, input_string:str, split_pattern: Pattern, word_limit: int) -> Optional[str]:
        raise NotImplementedError

    async def record_words(self, chopped_string:List[str]):
        pass

    async def generate_sentence(self, starting_word:str, word_limit: int):
        pass

    # def bulk_learn(self, sentences):
    #     pass
