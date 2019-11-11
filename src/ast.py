
import ast

from antlr4.tree import Tree

from .antlr.PyxellParser import PyxellParser
from .antlr.PyxellVisitor import PyxellVisitor

from .types import *
from .utils import *


def _node(ctx, name):
    return {
        'node': name,
        'position': [ctx.start.line, ctx.start.column + 1],
    }


class PyxellASTVisitor(PyxellVisitor):

    def visit(self, ctx):
        if ctx is None:
            return None
        if isinstance(ctx, list):
            return lmap(self.visit, ctx)
        if isinstance(ctx, Tree.TerminalNodeImpl):
            return str(ctx)
        return super().visit(ctx)


    ### Statements ###

    def visitProgram(self, ctx):
        return {
            **_node(ctx, 'Block'),
            'stmts': self.visit(ctx.stmt()),
        }

    def visitBlock(self, ctx):
        return {
            **_node(ctx, 'Block'),
            'stmts': self.visit(ctx.stmt()),
        }

    def visitStmt(self, ctx):
        return self.visit(ctx.simple_stmt() or ctx.compound_stmt())

    def visitStmtUse(self, ctx):
        if ctx.only:
            detail = ['only', *map(str, ctx.only.ID())]
        elif ctx.hiding:
            detail = ['hiding', *map(str, ctx.hiding.ID())]
        elif ctx.as_:
            detail = ['as', ctx.as_.text]
        else:
            detail = ['all']
        return {
            **_node(ctx, 'StmtUse'),
            'name': ctx.name.text,
            'detail': detail,
        }

    def visitStmtSkip(self, ctx):
        return {
            **_node(ctx, 'StmtSkip'),
        }

    def visitStmtPrint(self, ctx):
        return {
            **_node(ctx, 'StmtPrint'),
            'expr': self.visit(ctx.tuple_expr()),
        }

    def visitStmtDecl(self, ctx):
        return {
            **_node(ctx, 'StmtDecl'),
            'type': self.visit(ctx.typ()),
            'id': self.visit(ctx.ID()),
            'expr': self.visit(ctx.tuple_expr()),
        }

    def visitStmtAssg(self, ctx):
        return {
            **_node(ctx, 'StmtAssg'),
            'lvalues': self.visit(ctx.lvalue()),
            'expr': self.visit(ctx.tuple_expr()),
        }

    def visitLvalue(self, ctx):
        return {
            **_node(ctx, 'Lvalue'),
            'exprs': self.visit(ctx.expr()),
        }

    def visitStmtAssgExpr(self, ctx):
        return {
            **_node(ctx, 'StmtAssgExpr'),
            'exprs': self.visit(ctx.expr()),
            'op': ctx.op.text,
        }

    def visitStmtIf(self, ctx):
        return {
            **_node(ctx, 'StmtIf'),
            'exprs': self.visit(ctx.expr()),
            'blocks': self.visit(ctx.block()),
        }

    def visitStmtWhile(self, ctx):
        return {
            **_node(ctx, 'StmtWhile'),
            'expr': self.visit(ctx.expr()),
            'block': self.visit(ctx.block()),
        }

    def visitStmtUntil(self, ctx):
        return {
            **_node(ctx, 'StmtUntil'),
            'expr': self.visit(ctx.expr()),
            'block': self.visit(ctx.block()),
        }

    def visitStmtFor(self, ctx):
        exprs = ctx.tuple_expr()
        return {
            **_node(ctx, 'StmtFor'),
            'vars': self.visit(exprs[0].expr()),
            'iterables': self.visit(exprs[1].expr()),
            'steps': self.visit(exprs[2].expr()) if len(exprs) > 2 else [],
            'block': self.visit(ctx.block()),
        }

    def visitStmtLoopControl(self, ctx):
        return {
            **_node(ctx, 'StmtLoopControl'),
            'stmt': ctx.s.text,
        }

    def visitStmtFunc(self, ctx):
        return {
            **_node(ctx, 'StmtFunc'),
            'id': self.visit(ctx.ID()),
            'args': self.visit(ctx.func_arg()),
            'ret': self.visit(ctx.ret) or tVoid,
            'block': self.visit(ctx.block()),
        }

    def visitFuncArg(self, ctx):
        return {
            **_node(ctx, 'FuncArg'),
            'type': self.visit(ctx.typ()),
            'name': self.visit(ctx.ID()),
            'default': self.visit(ctx.expr()),
        }

    def visitStmtReturn(self, ctx):
        return {
            **_node(ctx, 'StmtReturn'),
            'expr': self.visit(ctx.tuple_expr()),
        }


    ### Expressions ###

    def visitExprParentheses(self, ctx):
        return self.visit(ctx.tuple_expr())

    def visitExprArray(self, ctx):
        return {
            **_node(ctx, 'ExprArray'),
            'exprs': self.visit(ctx.expr()),
        }

    def visitExprArrayComprehension(self, ctx):
        return {
            **_node(ctx, 'ExprArrayComprehension'),
            'expr': self.visit(ctx.expr()),
            'comprehensions': self.visit(ctx.comprehension()),
        }

    def visitComprehensionGenerator(self, ctx):
        exprs = ctx.tuple_expr()
        return {
            **_node(ctx, 'ComprehensionGenerator'),
            'vars': self.visit(exprs[0].expr()),
            'iterables': self.visit(exprs[1].expr()),
            'steps': self.visit(exprs[2].expr()) if len(exprs) > 2 else [],
        }

    def visitComprehensionFilter(self, ctx):
        return {
            **_node(ctx, 'ComprehensionFilter'),
            'expr': self.visit(ctx.expr()),
        }

    def visitExprIndex(self, ctx):
        return {
            **_node(ctx, 'ExprIndex'),
            'exprs': [self.visit(ctx.expr()), self.visit(ctx.tuple_expr())],
        }

    def visitExprSlice(self, ctx):
        return {
            **_node(ctx, 'ExprSlice'),
            'expr': self.visit(ctx.expr(0)),
            'slice': self.visit([ctx.e1, ctx.e2, ctx.e3]),
        }

    def visitExprAttr(self, ctx):
        return {
            **_node(ctx, 'ExprAttr'),
            'expr': self.visit(ctx.expr()),
            'attr': self.visit(ctx.ID()),
        }

    def visitExprCall(self, ctx):
        return {
            **_node(ctx, 'ExprCall'),
            'expr': self.visit(ctx.expr()),
            'args': self.visit(ctx.call_arg()),
        }

    def visitCallArg(self, ctx):
        return {
            **_node(ctx, 'CallArg'),
            'name': self.visit(ctx.ID()),
            'expr': self.visit(ctx.expr()),
        }

    def visitExprUnaryOp(self, ctx):
        return {
            **_node(ctx, 'ExprUnaryOp'),
            'expr': self.visit(ctx.expr()),
            'op': ctx.op.text,
        }

    def visitExprBinaryOp(self, ctx):
        return {
            **_node(ctx, 'ExprBinaryOp'),
            'exprs': self.visit(ctx.expr()),
            'op': ctx.op.text,
        }

    def visitExprRange(self, ctx):
        return {
            **_node(ctx, 'ExprRange'),
            'exprs': self.visit(ctx.expr()),
            'inclusive': ctx.dots.text == '..',
        }

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
        return {
            **_node(ctx, 'ExprCmp'),
            'exprs': self.visit(exprs),
            'ops': ops,
        }

    def visitExprLogicalOp(self, ctx):
        return {
            **_node(ctx, 'ExprLogicalOp'),
            'exprs': self.visit(ctx.expr()),
            'op': ctx.op.text,
        }

    def visitExprCond(self, ctx):
        return {
            **_node(ctx, 'ExprCond'),
            'exprs': self.visit(ctx.expr()),
        }

    def visitExprLambda(self, ctx):
        return {
            **_node(ctx, 'ExprLambda'),
            'ids': self.visit(ctx.ID()),
            'expr': self.visit(ctx.expr()),
        }

    def visitExprTuple(self, ctx):
        elems = self.visit(ctx.expr())
        if len(elems) == 1:
            return elems[0]
        return {
            **_node(ctx, 'ExprTuple'),
            'exprs': elems,
        }

    def visitExprInterpolation(self, ctx):
        return self.visit(ctx.tuple_expr())


    ### Atoms ###

    def visitAtomInt(self, ctx):
        return {
            **_node(ctx, 'AtomInt'),
            'int': int(self.visit(ctx.INT())),
        }

    def visitAtomFloat(self, ctx):
        return {
            **_node(ctx, 'AtomFloat'),
            'float': float(self.visit(ctx.FLOAT())),
        }

    def visitAtomBool(self, ctx):
        return {
            **_node(ctx, 'AtomBool'),
            'bool': ctx.getText() == 'true',
        }

    def visitAtomChar(self, ctx):
        return {
            **_node(ctx, 'AtomChar'),
            'char': ast.literal_eval(self.visit(ctx.CHAR())),
        }

    def visitAtomString(self, ctx):
        return {
            **_node(ctx, 'AtomString'),
            'string': ast.literal_eval(self.visit(ctx.STRING())),
        }

    def visitAtomNull(self, ctx):
        return {
            **_node(ctx, 'AtomNull'),
        }

    def visitAtomId(self, ctx):
        id = self.visit(ctx.ID())
        if id == '_':
            return _node(ctx, 'AtomStub')
        return {
            **_node(ctx, 'AtomId'),
            'id': id,
        }


    ### Types ###

    def visitTypePrimitive(self, ctx):
        return {
            'Void': tVoid,
            'Int': tInt,
            'Float': tFloat,
            'Bool': tBool,
            'Char': tChar,
            'String': tString,
        }[ctx.getText()]

    def visitTypeParentheses(self, ctx):
        return self.visit(ctx.typ())

    def visitTypeArray(self, ctx):
        return tArray(self.visit(ctx.typ()))

    def visitTypeNullable(self, ctx):
        return tNullable(self.visit(ctx.typ()))

    def visitTypeTuple(self, ctx):
        types = []
        while True:
            types.append(self.visit(ctx.typ(0)))
            if not isinstance(ctx.typ(1), PyxellParser.TypeTupleContext):
                break
            ctx = ctx.typ(1)
        types.append(self.visit(ctx.typ(1)))
        if len(types) == 1:
            return types[0]
        return tTuple(types)

    def visitTypeFunc(self, ctx):
        types = []
        while True:
            types.append(self.visit(ctx.typ(0)))
            if not isinstance(ctx.typ(1), PyxellParser.TypeFuncContext):
                break
            ctx = ctx.typ(1)
        types.append(self.visit(ctx.typ(1)))
        return tFunc(types[:-1], types[-1])

    def visitTypeFunc0(self, ctx):
        return tFunc([], self.visit(ctx.typ()))
