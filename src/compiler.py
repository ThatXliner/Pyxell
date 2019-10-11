
import ast
from contextlib import contextmanager

from .antlr.PyxellParser import PyxellParser
from .antlr.PyxellVisitor import PyxellVisitor
from .errors import PyxellError as err
from .types import *


class PyxellCompiler(PyxellVisitor):

    def __init__(self):
        self.env = {}
        self.builder = ll.IRBuilder()
        self.module = ll.Module()
        self.builtins = {
            'malloc': ll.Function(self.module, tFunc([tInt], tPtr()), 'malloc'),
            'write': ll.Function(self.module, tFunc([tString]), 'func.write'),
            'writeInt': ll.Function(self.module, tFunc([tInt]), 'func.writeInt'),
            'writeBool': ll.Function(self.module, tFunc([tBool]), 'func.writeBool'),
            'writeChar': ll.Function(self.module, tFunc([tChar]), 'func.writeChar'),
            'putchar': ll.Function(self.module, tFunc([tChar]), 'putchar'),
            'Int_pow': ll.Function(self.module, tFunc([tInt, tInt], tInt), 'func.Int_pow'),
        }


    ### Helpers ###

    @contextmanager
    def local(self):
        tmp = self.env.copy()
        yield
        self.env = tmp

    def throw(self, ctx, msg):
        raise err(msg, ctx.start.line, ctx.start.column+1)

    def get(self, ctx, id):
        try:
            return self.env[str(id)]
        except KeyError:
            self.throw(ctx, err.UndeclaredIdentifier(id))

    def index(self, ctx, *exprs):
        collection, index = [self.visit(expr) for expr in exprs]

        if collection.type.isString() or collection.type.isArray():
            index = self.cast(exprs[1], index, tInt)
            length = self.builder.extract_value(collection, [1])
            cmp = self.builder.icmp_signed('>=', index, vInt(0))
            index = self.builder.select(cmp, index, self.builder.add(index, length))
            return self.builder.gep(self.builder.extract_value(collection, [0]), [index])
        else:
            self.throw(ctx, err.NotIndexable(collection.type))

    def cast(self, ctx, value, type):
        if value.type != type:
            self.throw(ctx, err.IllegalAssignment(value.type, type))
        return value

    def unify(self, ctx, *values):
        if not all(values[0].type == value.type for value in values):
            self.throw(ctx, err.UnknownType())
        return values

    def lvalue(self, ctx, expr, declare=None):
        if isinstance(expr, PyxellParser.ExprAtomContext):
            atom = expr.atom()
            if not isinstance(atom, PyxellParser.AtomIdContext):
                self.throw(ctx, err.NotLvalue())
            id = str(atom.ID())
            if id not in self.env:
                if declare is None:
                    self.throw(ctx, err.UndeclaredIdentifier(id))
                self.env[id] = self.builder.alloca(declare)
            return self.env[id]
        elif isinstance(expr, PyxellParser.ExprIndexContext):
            return self.index(ctx, *expr.expr())
        else:
            self.throw(ctx, err.NotLvalue())

    def assign(self, ctx, expr, value):
        ptr = self.lvalue(ctx, expr, declare=value.type)
        value = self.cast(ctx, value, ptr.type.pointee)
        self.builder.store(value, ptr)

    def unaryop(self, ctx, op, value):
        if op in ('+', '-', '~'):
            type = tInt
        elif op == 'not':
            type = tBool

        if value.type != type:
            self.throw(ctx, err.NoUnaryOperator(op, value.type))

        if op == '+':
            return value
        elif op == '-':
            return self.builder.neg(value)
        elif op in ('~', 'not'):
            return self.builder.not_(value)

    def binaryop(self, ctx, op, left, right):
        if not left.type == right.type == tInt:
            self.throw(ctx, err.NoBinaryOperator(op, left.type, right.type))

        if op == '^':
            return self.builder.call(self.builtins['Int_pow'], [left, right])
        elif op == '/':
            v1 = self.builder.sdiv(left, right)
            v2 = self.builder.sub(v1, vInt(1))
            v3 = self.builder.xor(left, right)
            v4 = self.builder.icmp_signed('<', v3, vInt(0))
            v5 = self.builder.select(v4, v2, v1)
            v6 = self.builder.mul(v1, right)
            v7 = self.builder.icmp_signed('!=', v6, left)
            return self.builder.select(v7, v5, v1)
        elif op == '%':
            v1 = self.builder.srem(left, right)
            v2 = self.builder.add(v1, right)
            v3 = self.builder.xor(left, right)
            v4 = self.builder.icmp_signed('<', v3, vInt(0))
            v5 = self.builder.select(v4, v2, v1)
            v6 = self.builder.icmp_signed('==', v1, vInt(0))
            return self.builder.select(v6, v1, v5)
        else:
            instruction = {
                '*': self.builder.mul,
                '+': self.builder.add,
                '-': self.builder.sub,
                '<<': self.builder.shl,
                '>>': self.builder.ashr,
                '&': self.builder.and_,
                '$': self.builder.xor,
                '|': self.builder.or_,
            }[op]
            return instruction(left, right)

    def cmp(self, ctx, op, left, right):
        if left.type != right.type:
            self.throw(ctx, err.NotComparable(left.type, right.type))

        if left.type in (tInt, tChar):
            return self.builder.icmp_signed(op, left, right)
        elif left.type == tBool:
            return self.builder.icmp_unsigned(op, left, right)
        else:
            self.throw(ctx, err.NotComparable(left.type, right.type))

    def print(self, ctx, value):
        if value.type == tInt:
            self.builder.call(self.builtins['writeInt'], [value])
        elif value.type == tBool:
            self.builder.call(self.builtins['writeBool'], [value])
        elif value.type == tChar:
            self.builder.call(self.builtins['writeChar'], [value])
        elif value.type.isString():
            self.builder.call(self.builtins['write'], [value])
        elif value.type.isTuple():
            for i in range(len(value.type.elements)):
                if i > 0:
                    self.builder.call(self.builtins['putchar'], [vChar(' ')])
                elem = self.builder.extract_value(value, [i])
                self.print(ctx, elem)
        else:
            self.throw(ctx, err.NotPrintable(value.type))

    def malloc(self, type, n=1):
        size = self.builder.gep(vNull(type), [vIndex(n)])
        size = self.builder.ptrtoint(size, tInt)
        ptr = self.builder.call(self.builtins['malloc'], [size])
        return self.builder.bitcast(ptr, tPtr(type))


    ### Program ###

    def visitProgram(self, ctx):
        func = ll.Function(self.module, tFunc([], tInt), 'main')
        entry = func.append_basic_block()
        self.builder.position_at_end(entry)
        self.visitChildren(ctx)
        self.builder.position_at_end(func.blocks[-1])
        self.builder.ret(ll.Constant(tInt, 0))


    ### Statements ###

    def visitStmtPrint(self, ctx):
        expr = ctx.any_expr()
        if expr:
            value = self.visit(expr)
            self.print(expr, value)

        self.builder.call(self.builtins['putchar'], [vChar('\n')])

    def visitStmtAssg(self, ctx):
        value = self.visit(ctx.any_expr())

        for lvalue in ctx.lvalue():
            exprs = lvalue.expr()
            len1 = len(exprs)

            if value.type.isTuple():
                len2 = len(value.type.elements)
                if len1 > 1 and len1 != len2:
                    self.throw(ctx, err.CannotUnpack(value.type, len1))
            elif len1 > 1:
                self.throw(ctx, err.CannotUnpack(value.type, len1))

            if len1 == 1:
                self.assign(lvalue, exprs[0], value)
            else:
                for i, expr in enumerate(exprs):
                    self.assign(lvalue, expr, self.builder.extract_value(value, [i]))

    def visitStmtAssgExpr(self, ctx):
        ptr = self.lvalue(ctx, ctx.expr(0))
        value = self.binaryop(ctx, ctx.op.text, self.builder.load(ptr), self.visit(ctx.expr(1)))
        self.builder.store(value, ptr)

    def visitStmtIf(self, ctx):
        exprs = ctx.expr()
        blocks = ctx.block()

        bbend = ll.Block(self.builder.function)

        def emitIfElse(index):
            if len(exprs) == index:
                if len(blocks) > index:
                    with self.local():
                        self.visit(blocks[index])
                return

            expr = exprs[index]
            cond = self.cast(expr, self.visit(expr), tBool)

            bbif = self.builder.append_basic_block()
            bbelse = self.builder.append_basic_block()
            self.builder.cbranch(cond, bbif, bbelse)

            with self.builder._branch_helper(bbif, bbend):
                with self.local():
                    self.visit(blocks[index])

            with self.builder._branch_helper(bbelse, bbend):
                emitIfElse(index+1)

        emitIfElse(0)

        self.builder.function.blocks.append(bbend)
        self.builder.position_at_end(bbend)

    def visitStmtWhile(self, ctx):
        bbstart = self.builder.append_basic_block()
        self.builder.branch(bbstart)
        self.builder.position_at_end(bbstart)

        expr = ctx.expr()
        cond = self.cast(expr, self.visit(expr), tBool)

        bbwhile = self.builder.append_basic_block()
        bbend = ll.Block(self.builder.function)
        self.builder.cbranch(cond, bbwhile, bbend)

        self.builder.position_at_end(bbwhile)
        with self.local():
            self.visit(ctx.block())
        self.builder.branch(bbstart)

        self.builder.function.blocks.append(bbend)
        self.builder.position_at_end(bbend)

    def visitStmtUntil(self, ctx):
        bbuntil = self.builder.append_basic_block()
        self.builder.branch(bbuntil)
        bbend = ll.Block(self.builder.function)

        self.builder.position_at_end(bbuntil)
        with self.local():
            self.visit(ctx.block())

        expr = ctx.expr()
        cond = self.cast(expr, self.visit(expr), tBool)

        self.builder.cbranch(cond, bbend, bbuntil)

        self.builder.function.blocks.append(bbend)
        self.builder.position_at_end(bbend)


    ### Expressions ###

    def visitExprParentheses(self, ctx):
        return self.visit(ctx.any_expr())

    def visitExprIndex(self, ctx):
        return self.builder.load(self.index(ctx, *ctx.expr()))

    def visitExprAttr(self, ctx):
        value = self.visit(ctx.expr())
        id = str(ctx.ID())

        if value.type.isString() or value.type.isArray():
            if id != "length":
                self.throw(ctx, err.NoAttribute(value.type, id))

            return self.builder.extract_value(value, [1])

        elif value.type.isTuple():
            if len(id) > 1:
                self.throw(ctx, err.NoAttribute(value.type, id))

            index = ord(id) - ord('a')
            if not 0 <= index < len(value.type.elements):
                self.throw(ctx, err.NoAttribute(value.type, id))

            return self.builder.extract_value(value, [index])

        self.throw(ctx, err.NoAttribute(value.type, id))

    def visitExprUnaryOp(self, ctx):
        return self.unaryop(ctx, ctx.op.text, self.visit(ctx.expr()))

    def visitExprBinaryOp(self, ctx):
        return self.binaryop(ctx, ctx.op.text, self.visit(ctx.expr(0)), self.visit(ctx.expr(1)))

    def visitExprCmp(self, ctx):
        exprs = []
        ops = []
        while True:
            exprs.append(ctx.expr(0))
            ops.append(ctx.op.text)
            if not isinstance(ctx.expr(1), PyxellParser.ExprCmpContext):
                break
            ctx = ctx.expr(1)
        exprs.append(ctx.expr(1))

        values = [self.visit(exprs[0])]

        bbstart = self.builder.basic_block
        bbend = ll.Block(self.builder.function)
        self.builder.position_at_end(bbend)
        phi = self.builder.phi(tBool)
        self.builder.position_at_end(bbstart)

        def emitIf(index):
            values.append(self.visit(exprs[index+1]))
            cond = self.cmp(ctx, ops[index], values[index], values[index+1])

            if len(exprs) == index+2:
                phi.add_incoming(cond, self.builder.basic_block)
                self.builder.branch(bbend)
                return

            phi.add_incoming(vFalse, self.builder.basic_block)
            bbif = self.builder.function.append_basic_block()
            self.builder.cbranch(cond, bbif, bbend)

            with self.builder._branch_helper(bbif, bbend):
                emitIf(index+1)

        emitIf(0)

        self.builder.function.blocks.append(bbend)
        self.builder.position_at_end(bbend)

        return phi

    def visitExprLogicalOp(self, ctx):
        op = ctx.op.text

        cond1 = self.visit(ctx.expr(0))
        bbstart = self.builder.basic_block
        bbif = self.builder.function.append_basic_block()
        bbend = ll.Block(self.builder.function)

        if op == 'and':
            self.builder.cbranch(cond1, bbif, bbend)
        elif op == 'or':
            self.builder.cbranch(cond1, bbend, bbif)

        self.builder.position_at_end(bbend)
        phi = self.builder.phi(tBool)
        if op == 'and':
            phi.add_incoming(vFalse, bbstart)
        elif op == 'or':
            phi.add_incoming(vTrue, bbstart)

        with self.builder._branch_helper(bbif, bbend):
            cond2 = self.visit(ctx.expr(1))
            if not cond1.type == cond2.type == tBool:
                self.throw(ctx, err.NoBinaryOperator(op, cond1.type, cond2.type))
            phi.add_incoming(cond2, self.builder.basic_block)

        self.builder.function.blocks.append(bbend)
        self.builder.position_at_end(bbend)

        return phi

    def visitExprCond(self, ctx):
        exprs = ctx.expr()
        cond, *values = [self.visit(expr) for expr in exprs]

        cond = self.cast(exprs[0], cond, tBool)
        values = self.unify(ctx, *values)

        return self.builder.select(cond, *values)

    def visitExprTuple(self, ctx):
        exprs = ctx.expr()
        values = [self.visit(expr) for expr in exprs]

        type = tTuple(value.type for value in values)
        tuple = self.malloc(type)

        for i, value in enumerate(values):
            ptr = self.builder.gep(tuple, [vInt(0), vIndex(i)])
            self.builder.store(value, ptr)

        return self.builder.load(tuple)


    ### Atoms ###

    def visitAtomInt(self, ctx):
        return vInt(ctx.INT())

    def visitAtomBool(self, ctx):
        return vBool(ctx.getText() == 'true')

    def visitAtomChar(self, ctx):
        lit = ast.literal_eval(str(ctx.CHAR()))
        return vChar(lit)

    def visitAtomString(self, ctx):
        lit = ast.literal_eval(str(ctx.STRING()))
        values = [vChar(c) for c in lit]
        const = ll.Constant(ll.ArrayType(tChar, len(lit)), values)

        string = self.malloc(tString)

        pointer = self.builder.gep(string, [vInt(0), vIndex(0)])
        array = ll.GlobalVariable(self.module, const.type, self.module.get_unique_name('str'))
        array.global_constant = True
        array.initializer = const
        self.builder.store(self.builder.gep(array, [vInt(0), vInt(0)]), pointer)

        length = self.builder.gep(string, [vInt(0), vIndex(1)])
        self.builder.store(vInt(const.type.count), length)

        return self.builder.load(string)

    def visitAtomArray(self, ctx):
        exprs = ctx.expr()
        values = self.unify(ctx, *[self.visit(expr) for expr in exprs])

        subtype = values[0].type
        type = tArray(subtype)
        array = self.malloc(type)

        pointer = self.builder.gep(array, [vInt(0), vIndex(0)])
        memory = self.malloc(subtype, len(values))
        for i, value in enumerate(values):
            self.builder.store(value, self.builder.gep(memory, [vInt(i)]))
        self.builder.store(memory, pointer)

        length = self.builder.gep(array, [vInt(0), vIndex(1)])
        self.builder.store(vInt(len(values)), length)

        return self.builder.load(array)

    def visitAtomId(self, ctx):
        return self.builder.load(self.get(ctx, ctx.ID()))
