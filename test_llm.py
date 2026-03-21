import asyncio
from clone_checker import CloneChecker
async def main():
    import os
    api_key = os.environ.get("ZHIPUAI_API_KEY", "dummy")
    checker = CloneChecker(api_key=api_key)
    res = await checker.check([("def a(): pass", "def b(): pass")])
    print(res)
asyncio.run(main())
