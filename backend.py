# coding=utf-8
from tabulate import tabulate

EXPR = "expression"

syntax = {
    "start_while": ["WHILE", EXPR, "DO"], # Implemented
    "set_var": ["SET", EXPR, "TO", EXPR], # Implemented
    "display": ["SEND", EXPR, "TO DISPLAY"], # Implemented
    "if": ["IF", EXPR, "THEN"], # Implemented
    "else": ["ELSE"], # Implemented
    "end_if": ["END IF"], # Implemented
    "end_while": ["END WHILE"], # Implemented
    "start_for": ["FOR", EXPR, "FROM", EXPR, "TO", EXPR],
    "end_for": ["END FOR"],
    "for_each": ["FOR EACH", EXPR, "FROM", EXPR],
    # "new_func": ["FUNCTION", EXPR],
    # "return": ["RETURN", EXPR],
}


def match(line):
    line = line.strip()
    for possibility in syntax:
        pos = 0
        exprs = []
        for cmd in syntax[possibility]:
            if cmd == EXPR:
                continue
            loc = line[pos:].find(cmd)
            if loc == -1:
                break
            if line[pos:pos + loc].strip():
                exprs.append(line[pos:pos + loc].strip())
            pos += loc + len(cmd)
        else:
            if line[pos:].strip():
                exprs.append(line[pos:].strip())
            return possibility, exprs
    return "blank", []


def expression_evaluate(expression, var_dict):
    expression = expression.replace("^", "**")
    expression = expression.replace("=", "==")
    expression = expression.replace(">==", ">=")
    expression = expression.replace("<==", "<=")
    expression = expression.replace("!==", "!=")
    expression = expression.replace("(", " ( ")
    expression = expression.replace(")", " ) ")

    processed = ""

    canonical_forms = {"false": "False", "true": "True", "and": "and", "or": "or", "not": "not"}

    for part in expression.split():
        if part.lower() in canonical_forms:
            part = canonical_forms[part.lower()]
        processed += part + " "

    return eval(processed, {"__builitins__": None}, var_dict)


def skip_block(line_index, prog, enter_dels, exit_dels, reverse=False):
    if reverse:
        return skip_block_worker(line_index, prog, exit_dels, enter_dels, -1)
    else:
        return skip_block_worker(line_index, prog, enter_dels, exit_dels, 1)


def skip_block_worker(line_index, prog, enter_dels, exit_dels, delta):
    imbalance = 0
    while True:
        line_index += delta
        # print(line_index, imbalance, prog[line_index][0])
        if prog[line_index][0] in exit_dels:
            imbalance -= 1
            if imbalance < 0:
                break
        # print(line_index, imbalance)
        if prog[line_index][0] in enter_dels:
            imbalance += 1
        # print(line_index, imbalance)
    return line_index


class State:
    def __init__(self):
        self.__objects = {}
        self.__trace_table = [{}]
        self.temps = set()

    def __getitem__(self, item):
        if item not in self.__trace_table[-1]:
            self.temps.add(item)
        self.__trace_table[-1][item] = self.__objects[item]
        return self.__objects[item]

    def __setitem__(self, key, value):
        if key not in self.temps and key in self.__trace_table[-1] and self.__trace_table[-1][key] != value:
            self.new_frame()
        if key in self.temps:
            self.temps.remove(key)
        self.__trace_table[-1][key] = value
        self.__objects[key] = value

    def new_frame(self):
        if self.__trace_table[-1]:
            if len(self.temps | {"Display"}) == len(self.__trace_table[-1]):
                if "Display" in self.__trace_table[-1]:
                    self.__trace_table.pop()
                    self.__trace_table.append({"Display": self.__objects["Display"]})
                else:
                    self.__trace_table.pop()
            self.__trace_table.append({})
            self.temps = set()

    def get_objects(self):
        return self.__objects

    def get_trace_table(self):
        return self.__trace_table

    def print_trace_table(self):
        headers, rows = self.gen_trace_table()
        return tabulate(rows, headers=headers, tablefmt="html")

    def gen_trace_table(self):
        headers = sorted(i for i in self.__objects if i != "Display") + ["Display"]
        rows = [[state.get(header, None) for header in headers] for state in self.__trace_table]
        return headers, rows


def main(prog=None):
    if prog:
        prog = parse_code(prog)
    else:
        prog = read_program()
    # print("\n".join(str(x) for x in prog))

    line_index = 0
    # callback_stack = []
    for_stack = []  # (prev_line_index, current, target) OR (prev_line_index, arr_index)
    var_states = State()

    err = None

    while line_index < len(prog):
        # print("Line #:", line_index + 1)
        try:
            line = prog[line_index]
            code, exprs = line
            if code == "if":
                if expression_evaluate(exprs[0], var_states):
                    line_index += 1
                else:
                    line_index = skip_block(line_index, prog, ("if", "else"), ("else", "end_if")) + 1
            elif code == "else":
                line_index = skip_block(line_index, prog, ("if", "else"), ("else", "end_if")) + 1
            elif code == "end_if":
                line_index += 1

            elif code == "start_while":
                var_states.new_frame()
                if expression_evaluate(exprs[0], var_states):
                    line_index += 1
                else:
                    line_index = skip_block(line_index, prog, ("start_while",), ("end_while",)) + 1
            elif code == "end_while":
                line_index = skip_block(line_index, prog, ("start_while",), ("end_while",), reverse=True)

            elif code == "start_for":
                var_states.new_frame()
                if for_stack and for_stack[-1][0] == line_index:
                    state = for_stack[-1]
                    if state[1] == state[2]:
                        for_stack.pop()
                        line_index = skip_block(line_index, prog, ("start_for", "for_each"), ("end_for",))
                    else:
                        var_states[exprs[0]] = state[1] = state[1] + (state[2] - state[1] > 0)
                else:
                    start = expression_evaluate(exprs[1], var_states)
                    end = expression_evaluate(exprs[2], var_states)
                    for_stack.append([line_index, start, end])
                    var_states[exprs[0]] = start
                line_index += 1
            elif code == "for_each":
                var_states.new_frame()
                if for_stack and for_stack[-1][0] == line_index:
                    state = for_stack[-1]
                    if state[1] + 1 >= len(expression_evaluate(exprs[1], var_states)):
                        for_stack.pop()
                        line_index = skip_block(line_index, prog, ("start_for", "for_each",), ("end_for",))
                    else:
                        state[1] += 1
                        var_states[exprs[0]] = expression_evaluate(exprs[1], var_states)[state[1]]
                else:
                    for_stack.append([line_index, 0])
                    var_states[exprs[0]] = expression_evaluate(exprs[1], var_states)[0]
                line_index += 1
            elif code == "end_for":
                line_index = for_stack[-1][0]

            elif code == "set_var":
                var_states[exprs[0]] = expression_evaluate(exprs[1], var_states)
                line_index += 1
            elif code == "display":
                out = str(expression_evaluate(exprs[0], var_states))
                # var_states.new_frame()
                var_states["Display"] = out
                var_states.new_frame()
                # print(expression_evaluate(exprs[0], var_states))
                line_index += 1
            else:
                line_index += 1
        except Exception as e:
            err = e
            break

    return err, var_states


def parse_code(prog):
    return [match(a) for a in prog.split("\n")]


def read_program():
    prog = []
    while True:
        raw = input().split("\n")
        for a in raw:
            if a == "END":
                return prog
            prog.append(match(a))
