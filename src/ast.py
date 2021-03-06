
from antlr4.tree import Tree

from .parser.PyxellParser import PyxellParser
from .parser.PyxellVisitor import PyxellVisitor

from .utils import lmap


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

    def visitStmtUse(self, ctx):
        if ctx.hiding:
            detail = ['hiding', *self.visit(ctx.hiding)]
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
            'exprs': self.visit(ctx.expr()),
        }

    def visitStmtDecl(self, ctx):
        return {
            **_node(ctx, 'StmtDecl'),
            'id': self.visit(ctx.ID()),
            'type': self.visit(ctx.typ()),
            'expr': self.visit(ctx.tuple_expr()),
        }

    def visitStmtAssg(self, ctx):
        return {
            **_node(ctx, 'StmtAssg'),
            'lvalues': self.visit(ctx.tuple_expr()[:-1]),
            'expr': self.visit(ctx.tuple_expr()[-1]),
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
            'label': self.visit(ctx.ID()),
            'block': self.visit(ctx.block()),
        }

    def visitStmtUntil(self, ctx):
        return {
            **_node(ctx, 'StmtUntil'),
            'expr': self.visit(ctx.expr()),
            'label': self.visit(ctx.ID()),
            'block': self.visit(ctx.block()),
        }

    def visitStmtFor(self, ctx):
        exprs = ctx.tuple_expr()
        return {
            **_node(ctx, 'StmtFor'),
            'vars': self.visit(exprs[0].expr()),
            'iterables': self.visit(exprs[1].expr()),
            'label': self.visit(ctx.ID()),
            'block': self.visit(ctx.block()),
        }

    def visitStmtLoopControl(self, ctx):
        return {
            **_node(ctx, 'StmtLoopControl'),
            'stmt': ctx.s.text,
            'label': self.visit(ctx.ID()),
        }

    def _func_node(self, ctx, name):
        header = ctx.func_header()
        return {
            **_node(ctx, name),
            'id': self.visit(header.ID()),
            'typevars': self.visit(header.typevars) or [],
            'args': self.visit(header.func_arg()),
            'ret': self.visit(header.ret),
            'block': self.visit(ctx.block()),
            **({'generator': True} if header.generator else {}),
        }

    def visitStmtFunc(self, ctx):
        return self._func_node(ctx, 'StmtFunc')

    def visitFuncArg(self, ctx):
        return {
            **_node(ctx, 'FuncArg'),
            'name': self.visit(ctx.ID()),
            'type': self.visit(ctx.typ()),
            'default': self.visit(ctx.expr()),
            **({'variadic': True} if ctx.variadic else {}),
        }

    def visitStmtReturn(self, ctx):
        return {
            **_node(ctx, 'StmtReturn'),
            'expr': self.visit(ctx.tuple_expr()),
        }

    def visitStmtYield(self, ctx):
        return {
            **_node(ctx, 'StmtYield'),
            'expr': self.visit(ctx.tuple_expr()),
        }

    def visitStmtClass(self, ctx):
        return {
            **_node(ctx, 'StmtClass'),
            'id': self.visit(ctx.ID()),
            'base': self.visit(ctx.typ()),
            'members': self.visit(ctx.class_member()),
        }

    def visitClassField(self, ctx):
        return {
            **_node(ctx, 'ClassField'),
            'id': self.visit(ctx.ID()),
            'type': self.visit(ctx.typ()),
            'default': self.visit(ctx.tuple_expr()),
        }

    def visitClassMethod(self, ctx):
        return self._func_node(ctx, 'ClassMethod')

    def visitClassConstructor(self, ctx):
        return {
            **_node(ctx, 'ClassConstructor'),
            'id': '<constructor>',
            'args': [],
            'ret': {
                **_node(ctx, 'TypeName'),
                'name': 'Void',
            },
            'block': self.visit(ctx.block()),
        }

    def visitClassDestructor(self, ctx):
        return {
            **_node(ctx, 'ClassDestructor'),
            'id': '<destructor>',
            'args': [],
            'ret': {
                **_node(ctx, 'TypeName'),
                'name': 'Void',
            },
            'block': self.visit(ctx.block()),
        }


    ### Expressions ###

    def visitExprParentheses(self, ctx):
        return self.visit(ctx.tuple_expr())

    def visitExprArray(self, ctx):
        return {
            **_node(ctx, 'ExprCollection'),
            'kind': 'array',
            'exprs': self.visit(ctx.expr()),
        }

    def visitExprSet(self, ctx):
        return {
            **_node(ctx, 'ExprCollection'),
            'kind': 'set',
            'exprs': self.visit(ctx.expr()),
        }

    def visitExprDict(self, ctx):
        return {
            **_node(ctx, 'ExprDict'),
            'items': self.visit(ctx.dict_item()),
        }

    def visitDictPair(self, ctx):
        return {
            **_node(ctx, 'DictPair'),
            'exprs': self.visit(ctx.expr()),
        }

    def visitDictSpread(self, ctx):
        return {
            **_node(ctx, 'DictSpread'),
            'expr': self.visit(ctx.expr()),
        }

    def visitExprArrayComprehension(self, ctx):
        return {
            **_node(ctx, 'ExprComprehension'),
            'kind': 'array',
            'exprs': [self.visit(ctx.expr())],
            'comprehensions': self.visit(ctx.comprehension()),
        }

    def visitExprSetComprehension(self, ctx):
        return {
            **_node(ctx, 'ExprComprehension'),
            'kind': 'set',
            'exprs': [self.visit(ctx.expr())],
            'comprehensions': self.visit(ctx.comprehension()),
        }

    def visitExprDictComprehension(self, ctx):
        return {
            **_node(ctx, 'ExprComprehension'),
            'kind': 'dict',
            'exprs': self.visit(ctx.expr()),
            'comprehensions': self.visit(ctx.comprehension()),
        }

    def visitComprehensionIteration(self, ctx):
        exprs = ctx.tuple_expr()
        return {
            **_node(ctx, 'ComprehensionIteration'),
            'vars': self.visit(exprs[0].expr()),
            'iterables': self.visit(exprs[1].expr()),
        }

    def visitComprehensionPredicate(self, ctx):
        return {
            **_node(ctx, 'ComprehensionPredicate'),
            'expr': self.visit(ctx.expr()),
        }

    def visitExprAttr(self, ctx):
        return {
            **_node(ctx, 'ExprAttr'),
            'expr': self.visit(ctx.expr()),
            'attr': self.visit(ctx.ID()),
            **({'safe': True} if ctx.safe else {}),
        }

    def visitExprIndex(self, ctx):
        return {
            **_node(ctx, 'ExprIndex'),
            'exprs': [self.visit(ctx.expr()), self.visit(ctx.tuple_expr())],
            **({'safe': True} if ctx.safe else {}),
        }

    def visitExprSlice(self, ctx):
        return {
            **_node(ctx, 'ExprSlice'),
            'expr': self.visit(ctx.expr(0)),
            'slice': self.visit([ctx.e1, ctx.e2, ctx.e3]),
        }

    def visitExprCall(self, ctx):
        return {
            **_node(ctx, 'ExprCall'),
            'expr': self.visit(ctx.expr()),
            'args': self.visit(ctx.call_arg()),
            **({'partial': True} if ctx.partial else {}),
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

    def visitExprIsNull(self, ctx):
        return {
            **_node(ctx, 'ExprIsNull'),
            'expr': self.visit(ctx.expr()),
            **({'not': True} if ctx.not_ else {}),
        }

    def visitExprIn(self, ctx):
        return {
            **_node(ctx, 'ExprIn'),
            'exprs': self.visit(ctx.expr()),
            **({'not': True} if ctx.not_ else {}),
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

    def visitExprRange(self, ctx):
        return {
            **_node(ctx, 'ExprRange'),
            'exprs': self.visit(ctx.expr()),
            'inclusive': ctx.dots.text == '..',
        }

    def visitExprSpread(self, ctx):
        return {
            **_node(ctx, 'ExprSpread'),
            'expr': self.visit(ctx.expr()),
        }

    def visitExprBy(self, ctx):
        return {
            **_node(ctx, 'ExprBy'),
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
        number = ctx.getText().replace('_', '').lower()
        base = 2 if number.startswith('0b') else 8 if number.startswith('0o') else 16 if number.startswith('0x') else 10
        return {
            **_node(ctx, 'AtomInt'),
            'int': int(number, base),
        }

    def visitAtomRat(self, ctx):
        return {
            **_node(ctx, 'AtomRat'),
            'rat': ctx.getText().replace('_', '').replace('r', ''),
        }

    def visitAtomFloat(self, ctx):
        return {
            **_node(ctx, 'AtomFloat'),
            'float': float(ctx.getText().replace('_', '').replace('f', '')),
        }

    def visitAtomBool(self, ctx):
        return {
            **_node(ctx, 'AtomBool'),
            'bool': ctx.getText() == 'true',
        }

    def visitAtomChar(self, ctx):
        return {
            **_node(ctx, 'AtomChar'),
            'char': ctx.getText()[1:-1],
        }

    def visitAtomString(self, ctx):
        return {
            **_node(ctx, 'AtomString'),
            'string': ctx.getText()[1:-1],
        }

    def visitAtomNull(self, ctx):
        return {
            **_node(ctx, 'AtomNull'),
        }

    def visitAtomThis(self, ctx):
        return {
            **_node(ctx, 'AtomThis'),
        }

    def visitAtomSuper(self, ctx):
        return {
            **_node(ctx, 'AtomSuper'),
        }

    def visitAtomId(self, ctx):
        id = ctx.getText()
        if id == '_':
            return _node(ctx, 'AtomPlaceholder')
        return {
            **_node(ctx, 'AtomId'),
            'id': id,
        }

    def visitIdList(self, ctx):
        return self.visit(ctx.ID())


    ### Types ###

    def visitTypeName(self, ctx):
        return {
            **_node(ctx, 'TypeName'),
            'name': ctx.getText(),
        }

    def visitTypeParentheses(self, ctx):
        return self.visit(ctx.typ())

    def visitTypeArray(self, ctx):
        return {
            **_node(ctx, 'TypeArray'),
            'subtype': self.visit(ctx.typ()),
        }

    def visitTypeSet(self, ctx):
        return {
            **_node(ctx, 'TypeSet'),
            'subtype': self.visit(ctx.typ()),
        }

    def visitTypeDict(self, ctx):
        return {
            **_node(ctx, 'TypeDict'),
            'key_type': self.visit(ctx.typ(0)),
            'value_type': self.visit(ctx.typ(1)),
        }

    def visitTypeNullable(self, ctx):
        return {
            **_node(ctx, 'TypeNullable'),
            'subtype': self.visit(ctx.typ()),
        }

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
        return {
            **_node(ctx, 'TypeTuple'),
            'elements': types,
        }

    def visitTypeFunc(self, ctx):
        types = []
        while True:
            types.append(self.visit(ctx.typ(0)))
            if not isinstance(ctx.typ(1), PyxellParser.TypeFuncContext):
                break
            ctx = ctx.typ(1)
        types.append(self.visit(ctx.typ(1)))
        return {
            **_node(ctx, 'TypeFunc'),
            'args': types[:-1],
            'ret': types[-1],
        }

    def visitTypeFunc0(self, ctx):
        return {
            **_node(ctx, 'TypeFunc'),
            'args': [],
            'ret': self.visit(ctx.typ()),
        }
