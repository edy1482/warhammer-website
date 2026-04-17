class Token():
    def __init__(self, type_: str, value: str):
        self.type = type_
        self.value = value
    
    def __repr__(self):
        return f"{self.type} : {self.value}"
    

def tokenize(expression: str, known_keywords: list[str]) -> list[Token]:
    tokens: list[Token] = []
    # remove leading and trailing whitespace and standardise to uppercase
    remaining = expression.strip().upper()
    word_operators = ["AND", "OR", "NOT"]
    symbol_operators = ["(", ")"]
    # Need to use sorted known keywords by descending length:
    # Keyword may be multiple words like "BLOOD ANGELS"
    # Thus prefix matching, and using an ordered data structure is preferable

    sorted_known_keywords = sorted(known_keywords, key=len, reverse=True)

    while remaining:
        # remove leading whitespace
        remaining = remaining.lstrip()
        matched = False

        # Try matching with symbol operators
        for op in symbol_operators:
            if remaining.startswith(op):
                tokens.append(Token(op, op))
                remaining = remaining[len(op):]
                matched = True
                break
        
        if matched:
            continue

        # Try matching with word operators
        for op in word_operators:
            if remaining.startswith(op):
                end = len(op)
                # Check if next char is one of the paranthesis/space or has same length as remaining
                if end == len(remaining) or remaining[end] in " ()":
                    tokens.append(Token(op, op))
                    remaining = remaining[end:]
                    matched = True
                    break
        
        if matched:
            continue

        # Try matching with keywords
        for kw in sorted_known_keywords:
            if remaining.startswith(kw.upper()):
                tokens.append(Token("KEYWORD", kw))
                remaining = remaining[len(kw):]
                matched = True
                break

        if matched:
            continue
        
        # Return error if nothing matched
        char_buff = 20
        raise ValueError(f"Unknown token near {remaining[:char_buff]}")

    return tokens
