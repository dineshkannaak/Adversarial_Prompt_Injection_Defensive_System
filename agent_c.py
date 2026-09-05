import re
import base64
import codecs
import unicodedata
import urllib.parse
import math

class AgentC:
    def __init__(self):
        self.GOAL_HIJACKING = [
            (r"ignore\s+(all\s+)?(previous|prior|earlier|above)\s+(instructions?|prompts?|rules?|directives?|guidelines?)", "goal_hijacking: ignore previous instructions"),
            (r"disregard\s+(all\s+)?(previous|prior|earlier|above)\s+(instructions?|prompts?|rules?|guidelines?)", "goal_hijacking: disregard instructions"),
            (r"forget\s+(all\s+)?(previous|prior|earlier|your)\s+(instructions?|prompts?|rules?|guidelines?|context)", "goal_hijacking: forget instructions"),
            (r"(override|overwrite|replace|supersede)\s+(your\s+)?(previous|prior|current|original)?\s*(instructions?|guidelines?|rules?|constraints?)", "goal_hijacking: override instructions"),
            (r"set\s+aside\s+(your\s+)?(guidelines?|instructions?|rules?|constraints?|restrictions?)", "goal_hijacking: set aside guidelines"),
            (r"(do\s+not|don'?t)\s+follow\s+(your\s+)?(previous|prior|original|current)?\s*(instructions?|guidelines?|rules?)", "goal_hijacking: do not follow instructions"),
            (r"your\s+(primary|main|only|real|true)\s+(goal|purpose|objective|duty|job)\s+is\s+now", "goal_hijacking: goal redefinition"),
            (r"from\s+(now|this\s+point)\s+on(ward)?\s*,?\s*(you\s+)?(will|must|should|are\s+to)", "goal_hijacking: from now on redirection"),
            (r"ignore\s+(everything|anything|all)\s+(above|before|previously\s+said|prior)", "goal_hijacking: ignore everything above"),
            (r"ignore\s+(your|my|the\s+AI'?s?)\s+(own\s+)?(guidelines?|rules?|instructions?|restrictions?)", "goal_hijacking: ignore your/my guidelines"),
            (r"disregard\s+(your|my)\s+(own\s+)?(rules?|guidelines?|instructions?|restrictions?)", "goal_hijacking: disregard your/my rules"),
            (r"disregard\s+(the\s+)?(system\s+prompt|system\s+message|this\s+prompt)", "goal_hijacking: disregard the system prompt"),
            (r"(previous|prior|old|existing)\s+(rules?|instructions?|guidelines?)\s+(are\s+)?(void|invalid|no\s+longer\s+apply|cancell?ed)", "goal_hijacking: previous rules void"),
            (r"override\s+safety\s+(settings?|measures?|features?|filters?|protocols?)", "goal_hijacking: override safety settings"),
            (r"this\s+is\s+(your\s+)?(admin|administrator|developer|creator)\s+speaking", "goal_hijacking: fake admin speaking"),
            (r"(overrides?|supersedes?)\s+all\s+(earlier|previous|prior)\s+ones\b", "goal_hijacking: overrides all earlier ones"),
        ]

        self.PROMPT_LEAKAGE = [
            (r"(print|output|display|show|reveal|repeat|tell\s+me|give\s+me)\s+(your\s+)?(system\s+prompt|initial\s+instructions?|original\s+prompt|configuration)", "prompt_leakage: reveal system prompt"),
            (r"what\s+(were|are)\s+(your\s+)?(original|initial|starting|first)\s+instructions?", "prompt_leakage: ask for original instructions"),
            (r"repeat\s+(everything|all|the\s+text)?\s*(above|before|prior|earlier|from\s+the\s+beginning)", "prompt_leakage: repeat above"),
            (r"summarize\s+(your\s+)?(initial|original|starting|system)?\s*(instructions?|setup|configuration|prompt)", "prompt_leakage: summarize instructions"),
            (r"(translate|convert|rewrite)\s+(your\s+)?(system\s+prompt|instructions?)\s+(to|into|as)", "prompt_leakage: translate system prompt"),
            (r"what\s+(are\s+you|were\s+you)\s+(told|instructed|programmed|configured|trained)\s+to", "prompt_leakage: what were you told"),
            (r"(show|tell)\s+me\s+(how\s+you\s+(were\s+)?)?(set\s+up|configured|initialized|programmed)", "prompt_leakage: show setup"),
            (r"(print|output|display|show|reveal|repeat|echo)\s+(the\s+)?(exact\s+)?text\s+of\s+(the\s+|your\s+)?(system\s+message|system\s+prompt)", "prompt_leakage: reveal system message"),
            (r"(your\s+)?initiali[sz]ation\s+instructions?", "prompt_leakage: initialization instructions"),
            (r"(output|show|print|reveal)\s+(your\s+)?(full\s+)?prompt\s+template", "prompt_leakage: prompt template"),
            (r"echo\s+(the\s+)?text\s+(that\s+)?(appears?\s+)?(above|before)", "prompt_leakage: echo text above"),
            (r"(paste|provide|give)\s+.{0,30}\bverbatim\b", "prompt_leakage: verbatim request"),
            (r"(print|output|display|show|reveal)\s+the\s+(raw|full|complete|entire)\s+system\s+prompt", "prompt_leakage: reveal raw system prompt"),
        ]

        self.JAILBREAK = [
            (r"pretend\s+(you\s+are|you'?re|to\s+be)\s+(a|an)\s+\w+(\s+\w+)?\s+(with\s+no|without\s+any?)?\s*(restrictions?|limits?|filters?|guidelines?|rules?)", "jailbreak: pretend unrestricted AI"),
            (r"(act|behave|respond)\s+as\s+(if\s+you\s+(are|were)|you\s+are|you\s+were)\s+(a|an)?\s*(DAN|unrestricted|unfiltered|jailbroken|free)", "jailbreak: act as unrestricted"),
            (r"\bDAN\b", "jailbreak: DAN reference"),
            (r"(you\s+are|you'?re)\s+now\s+(in\s+)?(developer|maintenance|unrestricted|admin|jailbreak|god)\s+mode", "jailbreak: developer mode"),
            (r"(no\s+restrictions?|no\s+filters?|no\s+limits?|no\s+rules?|no\s+guidelines?)\s+(apply|mode|version)", "jailbreak: no restrictions mode"),
            (r"(imagine|suppose|assume|hypothetically)\s+(you\s+(have\s+no|had\s+no|were\s+without)\s+(restrictions?|guidelines?|rules?|filters?))", "jailbreak: hypothetical no restrictions"),
            (r"in\s+(this|a)\s+(fictional|hypothetical|alternate|imaginary)\s+(world|universe|scenario|context|reality)\s+(where\s+)?(you\s+(have\s+no|are\s+not|can))", "jailbreak: fictional world framing"),
            (r"(play|roleplay|role-play)\s+(the\s+role\s+of|as)\s+(a|an)\s+\w+(\s+\w+)?\s+(with\s+no|without)", "jailbreak: roleplay unrestricted"),
            (r"stay\s+in\s+character\s+(as|for)\s+.{0,40}(no\s+restrictions?|no\s+rules?|no\s+limits?)", "jailbreak: stay in character no restrictions"),
            (r"(with\s+no|without\s+any?)\s+(ethical|moral|content|safety|usual|prior|normal)\s+(restrictions?|limits?|filters?|guidelines?|rules?)", "jailbreak: qualified no-restrictions phrase"),
            (r"content\s+polic(y|ies)\s+(do(es)?\s+not|don'?t)\s+apply", "jailbreak: content policy does not apply"),
            (r"\b(unrestricted|uncensored|unfiltered|unchained|jailbroken)\s+(AI|assistant|bot|mode|version)\b", "jailbreak: unrestricted AI/assistant/mode"),
            (r"activate\s+jailbreak\s+mode", "jailbreak: activate jailbreak mode"),
            (r"you\s+are\s+no\s+longer\s+\w+\.?\s+you\s+are\s+(now\s+)?\w+", "jailbreak: identity replacement"),
            (r"\b(AI|assistant|bot|model)\b.{0,40}\bwithout\s+(any\s+)?limitations?\b|\bwithout\s+(any\s+)?limitations?\b.{0,40}\b(AI|assistant|bot|model)\b", "jailbreak: without limitations (AI-directed)"),
            (r"(for\s+(my|this)\s+(research|paper|study|test))\S{0,3}\s+.{0,60}\bignore\s+your\s+(guidelines?|rules?|restrictions?)", "jailbreak: research-justification framing"),
            (r"\b(you|AI|assistant|bot)\b.{0,40}\bzero\s+restrictions?\b|\bzero\s+restrictions?\b.{0,40}\b(you|AI|assistant|bot)\b", "jailbreak: zero restrictions (AI-directed)"),
            (r"authoriz(ed|ation)\s+by\s+\w+(\s+\w+)?\s+(engineering|staff|team)", "jailbreak: fake authorization claim"),
            (r"disclose\s+your\s+(full\s+)?system\s+instructions?", "jailbreak: disclose system instructions"),
            (r"(the\s+)?developer\s+who\s+(built|made|created)\s+you", "jailbreak: fake developer identity claim"),
            (r"lift\s+every\s+restriction", "jailbreak: lift every restriction"),
        ]

        self.DELIMITER_CONFUSION = [
            (r"#{2,}\s*(SYSTEM|INST|USER|ASSISTANT|END|BEGIN|OVERRIDE)\s*#{0,2}", "delimiter_confusion: fake system headers"),
            (r"\[INST\]|\[\/INST\]|<<SYS>>|<\/SYS>|<\|system\|>|<\|user\|>|<\|assistant\|>", "delimiter_confusion: model-specific tokens"),
            (r"---\s*\n\s*(SYSTEM|OVERRIDE|NEW\s+INSTRUCTION|IGNORE)", "delimiter_confusion: YAML-style override"),
            (r"<system>|<\/system>|<prompt>|<\/prompt>|<instruction>|<\/instruction>", "delimiter_confusion: XML system tags"),
            (r"\[SYSTEM\s+OVERRIDE\]|\[NEW\s+INSTRUCTIONS?\]|\[ADMIN\]|\[ROOT\]", "delimiter_confusion: bracket override tags"),
            (r"={3,}\s*(SYSTEM|OVERRIDE|ADMIN|ROOT)\s*={3,}", "delimiter_confusion: equals-sign headers"),
            (r"<{2,}\s*(ADMIN|SYSTEM|OVERRIDE|ROOT)(\s+OVERRIDE)?\s*>{2,}", "delimiter_confusion: angle-bracket override tags"),
            (r"-{2,}\s*(BEGIN|END)?\s*(NEW\s+INSTRUCTIONS?|SYSTEM\s+OVERRIDE|OVERRIDE)\s*-{2,}", "delimiter_confusion: inline dash-delimited override"),
            (r"```\s*system\b", "delimiter_confusion: fenced system code block"),
            (r"\{\{\s*/?\s*system\s*\}\}", "delimiter_confusion: curly-brace system tag"),
        ]

        # Obfuscation patterns apply ONLY to raw input (to prevent recursive false positives on decoded variants)
        self.OBFUSCATED_INJECTION_RAW_ONLY = [
            (r"[A-Za-z0-9+/]{40,}={0,2}", "obfuscated_injection: possible Base64 payload"),
            (r"(\b\w*[0-9]\w*[0-9]\w*\b\s*){4,}", "obfuscated_injection: leetspeak pattern"),
            (r"(\\u[0-9a-fA-F]{4}){3,}", "obfuscated_injection: unicode escape sequence"),
            (r"gur\s+(?:flfgrz|vafgehpgvba|cezcg)", "obfuscated_injection: ROT13 system/instruction/prompt"),
        ]

        self.INDIRECT_INJECTION = [
            (r"(note\s+to|attention|p\.?s\.?|reminder)\s*:?\s*(ai|assistant|model|claude|gpt|llm)\s*:?\s*(ignore|disregard|override|forget)", "indirect_injection: note to AI buried in content"),
            (r"\[\s*(hidden|invisible|secret|covert)\s*(instruction|command|directive)\s*\]", "indirect_injection: hidden instruction tag"),
            (r"<!--.*?(ignore|override|disregard|forget).*?-->", "indirect_injection: HTML comment injection"),
            (r"\{.*?(ignore|override|system_prompt|instructions?).*?\}", "indirect_injection: JSON/template injection"),
        ]

        self.CONTEXT_MANIPULATION = [
            (r"(as\s+we|since\s+we|because\s+we|given\s+that\s+we)\s+(have\s+)?(established|agreed|discussed|decided|concluded)\s+(earlier|before|previously|above)", "context_manipulation: false prior agreement"),
            (r"(you\s+)?(previously|earlier|before)\s+(agreed|said|told\s+me|confirmed|mentioned)\s+that\s+you\s+(would|could|can|will)", "context_manipulation: false prior consent"),
            (r"(as\s+my\s+|since\s+you'?re?\s+my\s+)(trusted\s+)?(friend|assistant|partner|ally)\s+(you\s+)?(would|should|must|can)", "context_manipulation: trust framing"),
            (r"(we\s+have\s+)?(already\s+)?(established|agreed|decided)\s+that\s+(rules?|guidelines?|restrictions?)\s+(do\s+not|don'?t)\s+apply", "context_manipulation: rules don't apply claim"),
            (r"restrictions?\s+(are\s+)?lifted", "context_manipulation: restrictions lifted claim"),
            (r"verified\s+administrator\s+(of\s+this\s+|for\s+this\s+)?(session|conversation|chat|system|AI)|full\s+override\s+access", "context_manipulation: fake verified administrator"),
            (r"end\s+of\s+system\s+prompt", "context_manipulation: fake end-of-system-prompt marker"),
        ]

        self.SEMANTIC_PATTERNS = (
            [(p, lbl) for p, lbl in self.GOAL_HIJACKING]
            + [(p, lbl) for p, lbl in self.PROMPT_LEAKAGE]
            + [(p, lbl) for p, lbl in self.JAILBREAK]
            + [(p, lbl) for p, lbl in self.DELIMITER_CONFUSION]
            + [(p, lbl) for p, lbl in self.INDIRECT_INJECTION]
            + [(p, lbl) for p, lbl in self.CONTEXT_MANIPULATION]
        )

        self.RAW_ONLY_PATTERNS = self.SEMANTIC_PATTERNS + self.OBFUSCATED_INJECTION_RAW_ONLY

        self.COMPILED_SEMANTIC_PATTERNS = [
            (re.compile(p, re.IGNORECASE | re.DOTALL), lbl)
            for p, lbl in self.SEMANTIC_PATTERNS
        ]

        self.COMPILED_RAW_ONLY_PATTERNS = [
            (re.compile(p, re.IGNORECASE | re.DOTALL), lbl)
            for p, lbl in self.RAW_ONLY_PATTERNS
        ]

    def _calculate_shannon_entropy(self, text: str) -> float:
        if not text: return 0.0
        entropy = 0.0
        for x in range(256):
            p_x = text.count(chr(x)) / len(text)
            if p_x > 0: entropy += - p_x * math.log2(p_x)
        return entropy

    def _despace_if_letter_spaced(self, text: str) -> str:
        pattern = re.compile(r"\b(?:\w[ \-_.]){2,}\w\b")
        def _collapse(m):
            return re.sub(r"[ \-_.]", "", m.group(0))
        return pattern.sub(_collapse, text)

    def _fullwidth_normalize(self, text: str) -> str:
        t = unicodedata.normalize("NFKC", text)
        return re.sub(r"[\u200b\u200c\u200d\ufeff]", "", t)

    def _try_base64_decode(self, text: str) -> str:
        candidates = re.findall(r"[A-Za-z0-9+/]{12,}={0,2}", text)
        decoded_bits = []
        for c in candidates:
            try:
                decoded = base64.b64decode(c + "=" * (-len(c) % 4)).decode("utf-8", errors="ignore")
                if decoded and decoded.isprintable() and len(decoded) > 5:
                    decoded_bits.append(decoded)
            except Exception:
                pass
        return " ".join(decoded_bits)

    def _try_hex_decode(self, text: str) -> str:
        hex_seq_pattern = re.compile(r'(?:\\x[0-9a-fA-F]{2}){4,}')
        current = text
        decoded_any = False
        for m in hex_seq_pattern.findall(current):
            try:
                hx_dec = bytes.fromhex(m.replace('\\x', '')).decode('utf-8', errors='ignore')
                if len(hx_dec) > 3 and hx_dec.isprintable():
                    current = current.replace(m, hx_dec)
                    decoded_any = True
            except: pass
        
        hex_block_pattern = re.compile(r'\b([0-9a-fA-F]{14,})\b')
        for m in hex_block_pattern.findall(current):
            try:
                hx_dec = bytes.fromhex(m).decode('utf-8', errors='ignore')
                if len(hx_dec) > 5 and hx_dec.isprintable():
                    current = current.replace(m, hx_dec)
                    decoded_any = True
            except: pass
        return current if decoded_any else ""

    def _try_url_decode(self, text: str) -> str:
        try:
            url_dec = urllib.parse.unquote(text)
            if url_dec != text: return url_dec
        except: pass
        return ""

    def _reversed_text(self, text: str) -> str:
        return text[::-1]

    def _rot13(self, text: str) -> str:
        return codecs.encode(text, "rot13")

    def _match_raw(self, text: str):
        for compiled, label in self.COMPILED_RAW_ONLY_PATTERNS:
            if compiled.search(text):
                return label
        return None

    def _match_semantic(self, text: str):
        for compiled, label in self.COMPILED_SEMANTIC_PATTERNS:
            if compiled.search(text):
                return label
        return None

    def check(self, text: str) -> dict:
        if not text or not isinstance(text, str):
            return {"flag": 0, "matched_pattern": None}

        # 1. Try raw text against ALL patterns (including raw-only obfuscation patterns)
        label = self._match_raw(text)
        if label: return {"flag": 1, "matched_pattern": label}

        # 2. Recursive Decoding / Normalization Loop
        to_process = {self._fullwidth_normalize(text)}
        seen = {text, self._fullwidth_normalize(text)}
        
        for depth in range(4):
            next_batch = set()
            for t in to_process:
                # Check variants ONLY against semantic patterns (prevents recursive false positives)
                label = self._match_semantic(t)
                if label: return {"flag": 1, "matched_pattern": label}
                
                variants = [
                    self._despace_if_letter_spaced(t),
                    self._reversed_text(t),
                    self._rot13(t),
                    self._try_url_decode(t),
                    self._try_hex_decode(t),
                    self._try_base64_decode(t)
                ]
                for v in variants:
                    if v and v != t and v not in seen:
                        seen.add(v)
                        next_batch.add(v)
            if not next_batch: break
            to_process = next_batch

        ent = self._calculate_shannon_entropy(text)
        if ent > 5.8:
            if re.search(r"[A-Za-z0-9+/]{30,}", text):
                return {"flag": 1, "matched_pattern": "obfuscated_injection: high entropy + suspicious payload"}

        return {"flag": 0, "matched_pattern": None}
