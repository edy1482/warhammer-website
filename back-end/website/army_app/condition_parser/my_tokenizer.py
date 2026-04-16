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
    operators = ["AND", "OR", "NOT", "(", ")"]
    # Need to use sorted known keywords by descending length:
    # Keyword may be multiple words like "BLOOD ANGELS"
    # Thus prefix matching, and using an ordered data structure is preferable

    sorted_known_keywords = sorted(known_keywords, key=len, reverse=True)

    while remaining:
        # remove leading whitespace
        remaining = remaining.lstrip()
        
        for op in operators:
            if remaining.startswith(op):
                tokens.append(Token(op, op))
                remaining = remaining[len(op):]
                break
            else:
                match = None
                for kw in sorted_known_keywords:
                    if remaining.startswith(kw.upper()):
                        match = kw
                        tokens.append(Token("KEYWORD", match))
                        break
                
                if not match:
                    # Return error showing up to the next 20 chars near token
                    char_buff = 20
                    raise ValueError(f"Unknown token near {remaining[:char_buff]}")
                
                remaining = remaining[len(match):]

    return tokens
