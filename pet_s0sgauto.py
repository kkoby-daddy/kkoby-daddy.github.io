# extract_pets_from_chat.py
import re, json, sys, argparse, pathlib

def read_text_auto(path: pathlib.Path):
    data = path.read_bytes()
    for enc in ("utf-8-sig","utf-8","cp949","euc-kr","utf-16","utf-16le","utf-16be"):
        try:
            return data.decode(enc), enc
        except Exception:
            pass
    return data.decode("utf-8", errors="replace"), "utf-8*replace"

def parse_chat(text: str):
    # [알림][파베로스]페트 검색 결과 입니다.
    pet_header = re.compile(r"^\[알림\]\[(?P<name>.+?)\]\s*페트\s*검색\s*결과", re.M)
    # [알림]√초기 : 레벨 1, 내구력 55.08, 공격력 11.90, 방어력 6.93, 순발력 9.00
    s0_re = re.compile(
        r"^\[알림\]\s*√초기\s*:\s*레벨\s*1[^,]*,\s*내구력\s*(?P<hp>\d+(?:\.\d+)?)\s*,\s*공격력\s*(?P<atk>\d+(?:\.\d+)?)\s*,\s*방어력\s*(?P<def>\d+(?:\.\d+)?)\s*,\s*순발력\s*(?P<agi>\d+(?:\.\d+)?)",
        re.M
    )
    # [알림]√성장 : 내구력 9.98 공격력 2.16, 방어력 1.26, 순발력 1.63, (…)
    sg_re = re.compile(
        r"^\[알림\]\s*√성장\s*:\s*내구력\s*(?P<hp>\d+(?:\.\d+)?)\s*[,]?\s*공격력\s*(?P<atk>\d+(?:\.\d+)?)\s*,\s*방어력\s*(?P<def>\d+(?:\.\d+)?)\s*,\s*순발력\s*(?P<agi>\d+(?:\.\d+)?)",
        re.M
    )

    pets = {}
    current = None
    for line in text.splitlines():
        m = pet_header.match(line)
        if m:
            current = m.group("name").strip()
            pets.setdefault(current, {"s0":{}, "sg":{}})
            continue
        if not current:
            continue
        ms0 = s0_re.match(line)
        if ms0 and not pets[current]["s0"]:
            pets[current]["s0"] = {k: float(v) for k,v in ms0.groupdict().items()}
            continue
        msg = sg_re.match(line)
        if msg and not pets[current]["sg"]:
            pets[current]["sg"] = {k: float(v) for k,v in msg.groupdict().items()}
            continue

    # s0/sg 둘 다 있는 케이스만
    return {k:v for k,v in pets.items() if v["s0"] and v["sg"]}

def merge_into(base: dict, new: dict):
    out = dict(base)
    for name, vals in new.items():
        if name in out and isinstance(out[name], dict):
            merged = dict(out[name])
            merged["s0"] = vals.get("s0", merged.get("s0", {}))
            merged["sg"] = vals.get("sg", merged.get("sg", {}))
            out[name] = merged
        else:
            out[name] = vals
    return out

def run(chat_path: pathlib.Path, out_path: pathlib.Path, merge_path: pathlib.Path|None):
    text, enc = read_text_auto(chat_path)
    parsed = parse_chat(text)
    if not parsed:
        print("추출 결과가 비었습니다. 원문 형식을 확인하세요.")
        return 2
    print(f"[INFO] 읽기 인코딩: {enc}, 추출 개수: {len(parsed)}")

    result = parsed
    if merge_path:
        base = json.loads(merge_path.read_text(encoding="utf-8"))
        result = merge_into(base, parsed)
        print(f"[INFO] 병합 완료: 기존 {len(base)} → 병합 후 {len(result)}")

    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] 저장: {out_path}")
    return 0

def main():
    p = argparse.ArgumentParser(description="CHAT_*.TXT에서 pets.json 스키마로 S0/SG 추출")
    p.add_argument("chat_txt", nargs="?", help="예: CHAT_250926.TXT")
    p.add_argument("-o","--out", help="출력 파일 경로(기본: 입력파일명 기반 .json)")
    p.add_argument("--merge", help="기존 pets.json과 병합(기존 필드 보존, s0/sg만 덮어씀)")
    args = p.parse_args()

    if not args.chat_txt:
        # 더블클릭용: 파일 선택 다이얼로그
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk(); root.withdraw()
            path = filedialog.askopenfilename(title="CHAT_*.TXT 선택", filetypes=[("Text","*.TXT *.txt"),("All","*.*")])
            if not path:
                print("파일을 선택하지 않았습니다.")
                sys.exit(2)
            args.chat_txt = path
        except Exception:
            print("사용법: python extract_pets_from_chat.py CHAT_*.TXT [-o out.json] [--merge pets.json]")
            sys.exit(2)

    chat_path = pathlib.Path(args.chat_txt)
    out_path = pathlib.Path(args.out) if args.out else chat_path.with_suffix(".pets.json")
    merge_path = pathlib.Path(args.merge) if args.merge else None
    sys.exit(run(chat_path, out_path, merge_path))

if __name__ == "__main__":
    main()
