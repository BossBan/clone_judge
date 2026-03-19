import asyncio
import csv
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from clone_checker import CloneChecker
from arg_parser import parse_args


def count_csv_rows(csv_path: Path) -> int:
    """统计单个csv文件的总行数"""
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        return sum(1 for _ in csv.reader(f))


def list_input_csv_files(csv_files: List[Path]) -> List[Path]:
    return csv_files


def build_code_file_index(bcb_root: Path) -> Dict[Tuple[str, str], List[Path]]:
    index: Dict[Tuple[str, str], List[Path]] = {}
    for file_path in sorted(bcb_root.rglob("*")):
        if not file_path.is_file():
            continue
        key = (file_path.parent.name, file_path.name)
        index.setdefault(key, []).append(file_path)
    return index


def resolve_code_file(
    file_index: Dict[Tuple[str, str], List[Path]],
    dir_name: str,
    file_name: str,
) -> Path:
    key = (dir_name, file_name)
    matches = file_index.get(key, [])
    if not matches:
        raise FileNotFoundError(f"Cannot locate source file for key={key}")
    return matches[0]


def read_code_segment(file_path: Path, start_line: int, end_line: int) -> str:
    if start_line <= 0 or end_line < start_line:
        raise ValueError(
            f"Invalid line range {start_line}-{end_line} for file {file_path}"
        )

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    start_idx = start_line - 1
    end_idx = end_line
    if start_idx >= len(lines):
        return ""
    return "".join(lines[start_idx:end_idx])


def extract_codes_for_row(
    row: List[str],
    file_index: Dict[Tuple[str, str], List[Path]],
) -> Tuple[str, str]:
    if len(row) < 8:
        raise ValueError(f"CSV row has {len(row)} columns, expected at least 8")

    dir1, file1, start1, end1, dir2, file2, start2, end2 = row[:8]
    source1 = resolve_code_file(file_index, dir1, file1)
    source2 = resolve_code_file(file_index, dir2, file2)

    code1 = read_code_segment(source1, int(start1), int(end1))
    code2 = read_code_segment(source2, int(start2), int(end2))
    return code1, code2


def normalize_verdict(result: object) -> str:
    if isinstance(result, Exception):
        return "ERROR"
    return "TRUE" if bool(result) else "FALSE"


def set_row_verdict(row: List[str], verdict: str) -> None:
    if len(row) >= 9:
        row[8] = verdict
    elif len(row) == 8:
        row.append(verdict)
    else:
        while len(row) < 8:
            row.append("")
        row.append(verdict)


def is_row_processed(row: List[str]) -> bool:
    return len(row) >= 9 and row[8] in ("TRUE", "FALSE")


def write_csv(csv_path: Path, rows: List[List[str]]) -> None:
    tmp_path = csv_path.with_name(csv_path.name + ".tmp")
    with open(tmp_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    tmp_path.replace(csv_path)


async def process_chunk(
    checker: CloneChecker,
    rows: List[List[str]],
    chunk_indices: List[int],
    file_index: Dict[Tuple[str, str], List[Path]],
    batch_size: int,
) -> None:
    valid_indices = []

    for idx in chunk_indices:
        row = rows[idx]
        try:
            _ = extract_codes_for_row(row, file_index)
            valid_indices.append(idx)
        except Exception as exc:
            set_row_verdict(row, "ERROR")
            print(f"Row {idx+1} error: {exc}")

    for start_idx in range(0, len(valid_indices), batch_size):
        batch_indices = valid_indices[start_idx : start_idx + batch_size]
        pairs = []
        for idx in batch_indices:
            code1, code2 = extract_codes_for_row(rows[idx], file_index)
            pairs.append((code1, code2))

        try:
            results = await checker.check(pairs)
        except Exception as exc:
            for idx in batch_indices:
                set_row_verdict(rows[idx], "ERROR")
            print(f"batch_check_failed: {exc}")
            continue

        for idx, result in zip(batch_indices, results):
            verdict = normalize_verdict(result)
            set_row_verdict(rows[idx], verdict)


async def process_one_csv(
    checker: CloneChecker,
    csv_path: Path,
    rows: List[List[str]],
    file_index: Dict[Tuple[str, str], List[Path]],
    csv_chunk_size: int,
    batch_size: int,
    total_rows: int,
    total_unprocessed: int,
) -> int:
    print(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Processing: {csv_path.name}"
    )

    processed = 0
    skipped = sum(1 for row in rows if is_row_processed(row))
    chunk_indices: List[int] = []

    for row_idx, row in enumerate(rows):
        if is_row_processed(row):
            continue

        chunk_indices.append(row_idx)
        if len(chunk_indices) >= csv_chunk_size:
            await process_chunk(
                checker=checker,
                rows=rows,
                chunk_indices=chunk_indices,
                file_index=file_index,
                batch_size=batch_size,
            )
            write_csv(csv_path, rows)

            processed += len(chunk_indices)
            percent = (
                (processed / total_unprocessed * 100) if total_unprocessed else 100.0
            )
            print(
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]   Progress: {processed} rows processed, {skipped} rows skipped, {percent:.2f}% done in this csv"
            )
            chunk_indices.clear()

    if chunk_indices:
        await process_chunk(
            checker=checker,
            rows=rows,
            chunk_indices=chunk_indices,
            file_index=file_index,
            batch_size=batch_size,
        )
        write_csv(csv_path, rows)

        processed += len(chunk_indices)
        percent = (processed / total_unprocessed * 100) if total_unprocessed else 100.0
        print(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]   Progress: {processed} rows processed, {skipped} rows skipped, {percent:.2f}% done in this csv"
        )

    print(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]   Finished processing: {processed} rows processed, {skipped} rows skipped"
    )

    true_count = sum(1 for row in rows if len(row) >= 9 and row[8] == "TRUE")
    false_count = sum(1 for row in rows if len(row) >= 9 and row[8] == "FALSE")
    total_valid = true_count + false_count

    if total_valid > 0:
        true_ratio = (true_count / total_valid) * 100
        false_ratio = (false_count / total_valid) * 100
        print(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]   Result summary for {csv_path.name}: TRUE: {true_count} ({true_ratio:.2f}%), FALSE: {false_count} ({false_ratio:.2f}%)"
        )
    else:
        print(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]   Result summary for {csv_path.name}: No valid TRUE/FALSE results found."
        )

    return processed


async def main() -> None:
    args = parse_args()

    if not args.api_key:
        raise ValueError("API key is required. Use --api-key or set ZHIPUAI_API_KEY.")

    data_dir = getattr(args, "code_dir", getattr(args, "data_dir", Path("data")))
    bcb_dir = data_dir / "bcb_reduced"
    if not bcb_dir.exists():
        raise FileNotFoundError(f"bcb directory not found: {bcb_dir}")

    input_csv_files = list_input_csv_files(args.csv_files)
    if not input_csv_files:
        print("No input CSV files provided.")
        return

    file_index = build_code_file_index(bcb_dir)
    checker = CloneChecker(
        api_key=args.api_key,
        timeout=args.timeout,
        concurrency_limit=args.concurrency_limit,
        prompt_file=str(args.prompt_file),
    )

    total_rows = 0
    total_unprocessed = 0
    csv_row_stats = {}
    print("Counting total and unprocessed rows for all CSVs...")

    # Optional logic to pick sampled rows if lines parameter is set
    filtered_csv_rows = {}

    for csv_path in input_csv_files:
        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            all_rows = list(csv.reader(f))

        if args.lines is not None and args.lines < len(all_rows):
            selected_rows = random.sample(all_rows, args.lines)
        else:
            selected_rows = all_rows

        filtered_csv_rows[csv_path.name] = selected_rows

        nrows = len(selected_rows)
        nprocessed = sum(1 for r in selected_rows if is_row_processed(r))
        nunprocessed = nrows - nprocessed

        csv_row_stats[csv_path.name] = (nrows, nunprocessed)
        total_rows += nrows
        total_unprocessed += nunprocessed
        print(f"  {csv_path.name}: total {nrows}, unprocessed {nunprocessed}")
    print(f"Total rows: {total_rows}, total unprocessed: {total_unprocessed}")

    processed_sum = 0
    for csv_path in input_csv_files:
        nrows, nunprocessed = csv_row_stats[csv_path.name]
        selected_rows = filtered_csv_rows[csv_path.name]
        try:
            processed = await process_one_csv(
                checker=checker,
                csv_path=csv_path,
                rows=selected_rows,
                file_index=file_index,
                csv_chunk_size=args.csv_chunk_size,
                batch_size=args.batch_size,
                total_rows=nrows,
                total_unprocessed=nunprocessed,
            )
            processed_sum += processed
            percent_all = (
                (processed_sum / total_unprocessed * 100)
                if total_unprocessed
                else 100.0
            )
            print(
                f"[ALL CSVs] Progress: {processed_sum}/{total_unprocessed} ({percent_all:.2f}%)"
            )
        except Exception as exc:
            print(
                f"ERROR: failed processing {csv_path.name}, continue next file: {exc}"
            )

    print("All done. Results written back to CSV files.")


if __name__ == "__main__":
    asyncio.run(main())
