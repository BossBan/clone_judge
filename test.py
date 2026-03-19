import asyncio
from clone_checker import CloneChecker

# 代码片段示例
code1 = "def add(a, b): return a + b"
code2 = "def sum(x, y): return x + y"


async def main():
    checker = CloneChecker(api_key="f53c763c7c4c498e884cd3c3ebec8ca2.1IOwLwLi105s6tCe")
    pairs = [(code1, code2), (code1, "print('hello')")]
    results = await checker.check(pairs)
    print(f"Batch Results: {results}")


if __name__ == "__main__":
    asyncio.run(main())
