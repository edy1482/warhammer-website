from tokenizer import Token

# ------------------------
# Recursive Descent Parser
# ------------------------
class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def current(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def eat(self, token_type: str):
        token = self.current()
        if not token or token.type != token_type:
            raise ValueError(f"Expected {token_type}, got {token}")
        self.pos += 1
        return token

    # Entry point
    def parse_expression(self):
        node = self.parse_or()
        if self.current() is not None:
            raise ValueError(f"Unexpected trailing token: {self.current()}")
        return node

    # OR level
    def parse_or(self):
        node = self.parse_and()  # <-- Step 3.1: parse the left-hand side of OR/AND recursively
        while self.current() and self.current().type == "OR":
            self.eat("OR")
            right = self.parse_and()  # <-- Step 3.2: recursive call for right-hand side of OR
            node = ("OR", [node, right])
        return node

    # AND level
    def parse_and(self):
        node = self.parse_factor()  # <-- Step 3.3: recursive call to parse_factor for the left-hand side
        while self.current() and self.current().type == "AND":
            self.eat("AND")
            right = self.parse_factor()  # <-- Step 3.4: recursive call for right-hand side of AND
            node = ("AND", [node, right])
        return node

    # Factor level: NOT / parentheses / keyword
    def parse_factor(self):
        token = self.current()
        if token.type == "NOT":
            self.eat("NOT")
            child = self.parse_factor()  # <-- Step 3.5: recursive call for NOT child
            return ("NOT", [child])
        elif token.type == "(":
            self.eat("(")
            node = self.parse_expression()  # <-- Step 3.6: recursive call for expression inside parentheses
            self.eat(")")
            return node
        elif token.type == "KEYWORD":
            self.eat("KEYWORD")  # <-- Step 3.7: base case, leaf node for keyword
            return ("KEYWORD", token.value)
        else:
            raise ValueError(f"Unexpected token: {token}")