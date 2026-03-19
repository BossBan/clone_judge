import asyncio
from zai import ZhipuAiClient


class CloneChecker:
    def __init__(
        self,
        api_key: str,
        timeout: int = 60,
        concurrency_limit: int = 200,
        prompt_file: str = "prompt_template.txt",
    ):
        """
        Initialize the CloneChecker.

        Args:
            api_key (str, optional): The Zhipu AI API Key. If not provided, it will be read from the ZHIPUAI_API_KEY environment variable.
            timeout (int, optional): Overall timeout (seconds) for batch checks.
            concurrency_limit (int, optional): limit for concurrent api calls.
            prompt_file (str, optional): path to the prompt template file.
        """
        self.api_key = api_key
        if not self.api_key:
            raise ValueError("API Key is required.")
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(concurrency_limit)
        self.client = ZhipuAiClient(api_key=self.api_key)
        with open(prompt_file, "r", encoding="utf-8") as f:
            self.prompt_template = f.read()

    async def _check_is_clone(self, code1: str, code2: str) -> bool:
        prompt = self.prompt_template.format(code1=code1, code2=code2)
        model = "glm-4-flash"

        async with self.semaphore:
            res = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )

            if res and res.choices:
                content = res.choices[0].message.content.strip()
                # DEBUG: print the raw content
                # print(f"DEBUG: Model response content: {content}")
                import re

                match = re.search(r'clone_type\s*:\s*"?(\d)', content)
                if match:
                    clone_type = match.group(1)
                    return clone_type != "0"

                raise ValueError(f"Unexpected model response format: {content}")
            else:
                raise ValueError("No response from model or empty choices.")

    async def check(self, pairs: list[tuple[str, str]]) -> list:
        """
        Check a batch of code pairs.
        """
        tasks = [asyncio.create_task(self._check_is_clone(c1, c2)) for c1, c2 in pairs]
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks), timeout=self.timeout
            )
            return list(results)
        except asyncio.TimeoutError:
            # Cancel any pending tasks if timeout occurs
            for t in tasks:
                if not t.done():
                    t.cancel()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return list(results)
