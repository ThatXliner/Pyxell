{-# LANGUAGE FlexibleInstances, OverlappingInstances #-}
{-# OPTIONS_GHC -fno-warn-incomplete-patterns #-}

-- | Pretty-printer for PrintPyxell.
--   Generated by the BNF converter.

module PrintPyxell where

import AbsPyxell
import Data.Char

-- | The top-level printing method.

printTree :: Print a => a -> String
printTree = render . prt 0

type Doc = [ShowS] -> [ShowS]

doc :: ShowS -> Doc
doc = (:)

render :: Doc -> String
render d = rend 0 (map ($ "") $ d []) "" where
  rend i ss = case ss of
    "["      :ts -> showChar '[' . rend i ts
    "("      :ts -> showChar '(' . rend i ts
    "{"      :ts -> showChar '{' . new (i+1) . rend (i+1) ts
    "}" : ";":ts -> new (i-1) . space "}" . showChar ';' . new (i-1) . rend (i-1) ts
    "}"      :ts -> new (i-1) . showChar '}' . new (i-1) . rend (i-1) ts
    ";"      :ts -> showChar ';' . new i . rend i ts
    t  : ts@(p:_) | closingOrPunctuation p -> showString t . rend i ts
    t        :ts -> space t . rend i ts
    _            -> id
  new i   = showChar '\n' . replicateS (2*i) (showChar ' ') . dropWhile isSpace
  space t = showString t . (\s -> if null s then "" else ' ':s)

  closingOrPunctuation :: String -> Bool
  closingOrPunctuation [c] = c `elem` closerOrPunct
  closingOrPunctuation _   = False

  closerOrPunct :: String
  closerOrPunct = ")],;"

parenth :: Doc -> Doc
parenth ss = doc (showChar '(') . ss . doc (showChar ')')

concatS :: [ShowS] -> ShowS
concatS = foldr (.) id

concatD :: [Doc] -> Doc
concatD = foldr (.) id

replicateS :: Int -> ShowS -> ShowS
replicateS n f = concatS (replicate n f)

-- | The printer class does the job.

class Print a where
  prt :: Int -> a -> Doc
  prtList :: Int -> [a] -> Doc
  prtList i = concatD . map (prt i)

instance Print a => Print [a] where
  prt = prtList

instance Print Char where
  prt _ s = doc (showChar '\'' . mkEsc '\'' s . showChar '\'')
  prtList _ s = doc (showChar '"' . concatS (map (mkEsc '"') s) . showChar '"')

mkEsc :: Char -> Char -> ShowS
mkEsc q s = case s of
  _ | s == q -> showChar '\\' . showChar s
  '\\'-> showString "\\\\"
  '\n' -> showString "\\n"
  '\t' -> showString "\\t"
  _ -> showChar s

prPrec :: Int -> Int -> Doc -> Doc
prPrec i j = if j < i then parenth else id

instance Print Integer where
  prt _ x = doc (shows x)

instance Print Double where
  prt _ x = doc (shows x)

instance Print Ident where
  prt _ (Ident i) = doc (showString i)
  prtList _ [] = concatD []
  prtList _ [x] = concatD [prt 0 x]
  prtList _ (x:xs) = concatD [prt 0 x, doc (showString ","), prt 0 xs]

instance Print (Program a) where
  prt i e = case e of
    Program _ stmts -> prPrec i 0 (concatD [prt 0 stmts])

instance Print [Stmt a] where
  prt = prtList

instance Print (Stmt a) where
  prt i e = case e of
    SProc _ id argfs block -> prPrec i 0 (concatD [doc (showString "func"), prt 0 id, doc (showString "("), prt 0 argfs, doc (showString ")"), doc (showString "def"), prt 0 block])
    SFunc _ id argfs type_ block -> prPrec i 0 (concatD [doc (showString "func"), prt 0 id, doc (showString "("), prt 0 argfs, doc (showString ")"), prt 0 type_, doc (showString "def"), prt 0 block])
    SProcExtern _ id argfs -> prPrec i 0 (concatD [doc (showString "func"), prt 0 id, doc (showString "("), prt 0 argfs, doc (showString ")"), doc (showString "extern")])
    SFuncExtern _ id argfs type_ -> prPrec i 0 (concatD [doc (showString "func"), prt 0 id, doc (showString "("), prt 0 argfs, doc (showString ")"), prt 0 type_, doc (showString "extern")])
    SRetVoid _ -> prPrec i 0 (concatD [doc (showString "return")])
    SRetExpr _ expr -> prPrec i 0 (concatD [doc (showString "return"), prt 0 expr])
    SSkip _ -> prPrec i 0 (concatD [doc (showString "skip")])
    SPrint _ expr -> prPrec i 0 (concatD [doc (showString "print"), prt 0 expr])
    SPrintEmpty _ -> prPrec i 0 (concatD [doc (showString "print")])
    SAssg _ exprs -> prPrec i 0 (concatD [prt 0 exprs])
    SAssgMul _ expr1 expr2 -> prPrec i 0 (concatD [prt 0 expr1, doc (showString "*="), prt 0 expr2])
    SAssgDiv _ expr1 expr2 -> prPrec i 0 (concatD [prt 0 expr1, doc (showString "/="), prt 0 expr2])
    SAssgMod _ expr1 expr2 -> prPrec i 0 (concatD [prt 0 expr1, doc (showString "%="), prt 0 expr2])
    SAssgAdd _ expr1 expr2 -> prPrec i 0 (concatD [prt 0 expr1, doc (showString "+="), prt 0 expr2])
    SAssgSub _ expr1 expr2 -> prPrec i 0 (concatD [prt 0 expr1, doc (showString "-="), prt 0 expr2])
    SIf _ branchs else_ -> prPrec i 0 (concatD [doc (showString "if"), prt 0 branchs, prt 0 else_])
    SWhile _ expr block -> prPrec i 0 (concatD [doc (showString "while"), prt 0 expr, doc (showString "do"), prt 0 block])
    SUntil _ expr block -> prPrec i 0 (concatD [doc (showString "until"), prt 0 expr, doc (showString "do"), prt 0 block])
    SFor _ expr1 expr2 block -> prPrec i 0 (concatD [doc (showString "for"), prt 0 expr1, doc (showString "in"), prt 0 expr2, doc (showString "do"), prt 0 block])
    SForStep _ expr1 expr2 expr3 block -> prPrec i 0 (concatD [doc (showString "for"), prt 0 expr1, doc (showString "in"), prt 0 expr2, doc (showString "step"), prt 0 expr3, doc (showString "do"), prt 0 block])
    SContinue _ -> prPrec i 0 (concatD [doc (showString "continue")])
    SBreak _ -> prPrec i 0 (concatD [doc (showString "break")])
  prtList _ [] = concatD []
  prtList _ [x] = concatD [prt 0 x]
  prtList _ (x:xs) = concatD [prt 0 x, doc (showString ";"), prt 0 xs]

instance Print (ArgF a) where
  prt i e = case e of
    ANoDefault _ type_ id -> prPrec i 0 (concatD [prt 0 type_, prt 0 id])
    ADefault _ type_ id expr -> prPrec i 0 (concatD [prt 0 type_, prt 0 id, doc (showString ":"), prt 2 expr])
  prtList _ [] = concatD []
  prtList _ [x] = concatD [prt 0 x]
  prtList _ (x:xs) = concatD [prt 0 x, doc (showString ","), prt 0 xs]

instance Print [ArgF a] where
  prt = prtList

instance Print (Block a) where
  prt i e = case e of
    SBlock _ stmts -> prPrec i 0 (concatD [doc (showString "{"), prt 0 stmts, doc (showString "}")])

instance Print [Expr a] where
  prt = prtList

instance Print (Branch a) where
  prt i e = case e of
    BElIf _ expr block -> prPrec i 0 (concatD [prt 0 expr, doc (showString "do"), prt 0 block])
  prtList _ [] = concatD []
  prtList _ [x] = concatD [prt 0 x]
  prtList _ (x:xs) = concatD [prt 0 x, doc (showString "elif"), prt 0 xs]

instance Print [Branch a] where
  prt = prtList

instance Print (Else a) where
  prt i e = case e of
    EElse _ block -> prPrec i 0 (concatD [doc (showString "else"), doc (showString "do"), prt 0 block])
    EEmpty _ -> prPrec i 0 (concatD [])

instance Print (ArgC a) where
  prt i e = case e of
    APos _ expr -> prPrec i 0 (concatD [prt 2 expr])
    ANamed _ id expr -> prPrec i 0 (concatD [prt 0 id, doc (showString "="), prt 2 expr])
  prtList _ [] = concatD []
  prtList _ [x] = concatD [prt 0 x]
  prtList _ (x:xs) = concatD [prt 0 x, doc (showString ","), prt 0 xs]

instance Print [ArgC a] where
  prt = prtList

instance Print (Cmp a) where
  prt i e = case e of
    Cmp1 _ expr1 cmpop expr2 -> prPrec i 0 (concatD [prt 6 expr1, prt 0 cmpop, prt 6 expr2])
    Cmp2 _ expr cmpop cmp -> prPrec i 0 (concatD [prt 6 expr, prt 0 cmpop, prt 0 cmp])

instance Print (CmpOp a) where
  prt i e = case e of
    CmpEQ _ -> prPrec i 0 (concatD [doc (showString "==")])
    CmpNE _ -> prPrec i 0 (concatD [doc (showString "!=")])
    CmpLT _ -> prPrec i 0 (concatD [doc (showString "<")])
    CmpLE _ -> prPrec i 0 (concatD [doc (showString "<=")])
    CmpGT _ -> prPrec i 0 (concatD [doc (showString ">")])
    CmpGE _ -> prPrec i 0 (concatD [doc (showString ">=")])

instance Print [Ident] where
  prt = prtList

instance Print (Expr a) where
  prt i e = case e of
    EStub _ -> prPrec i 10 (concatD [doc (showString "_")])
    EInt _ n -> prPrec i 10 (concatD [prt 0 n])
    ETrue _ -> prPrec i 10 (concatD [doc (showString "true")])
    EFalse _ -> prPrec i 10 (concatD [doc (showString "false")])
    EChar _ c -> prPrec i 10 (concatD [prt 0 c])
    EString _ str -> prPrec i 10 (concatD [prt 0 str])
    EArray _ exprs -> prPrec i 10 (concatD [doc (showString "["), prt 2 exprs, doc (showString "]")])
    EVar _ id -> prPrec i 10 (concatD [prt 0 id])
    EElem _ expr n -> prPrec i 10 (concatD [prt 10 expr, doc (showString "."), prt 0 n])
    EIndex _ expr1 expr2 -> prPrec i 10 (concatD [prt 10 expr1, doc (showString "["), prt 0 expr2, doc (showString "]")])
    EAttr _ expr id -> prPrec i 10 (concatD [prt 10 expr, doc (showString "."), prt 0 id])
    ECall _ expr argcs -> prPrec i 10 (concatD [prt 10 expr, doc (showString "("), prt 0 argcs, doc (showString ")")])
    EPow _ expr1 expr2 -> prPrec i 9 (concatD [prt 10 expr1, doc (showString "**"), prt 9 expr2])
    EMul _ expr1 expr2 -> prPrec i 8 (concatD [prt 8 expr1, doc (showString "*"), prt 9 expr2])
    EDiv _ expr1 expr2 -> prPrec i 8 (concatD [prt 8 expr1, doc (showString "/"), prt 9 expr2])
    EMod _ expr1 expr2 -> prPrec i 8 (concatD [prt 8 expr1, doc (showString "%"), prt 9 expr2])
    EAdd _ expr1 expr2 -> prPrec i 7 (concatD [prt 7 expr1, doc (showString "+"), prt 8 expr2])
    ESub _ expr1 expr2 -> prPrec i 7 (concatD [prt 7 expr1, doc (showString "-"), prt 8 expr2])
    ENeg _ expr -> prPrec i 7 (concatD [doc (showString "-"), prt 8 expr])
    ERangeIncl _ expr1 expr2 -> prPrec i 6 (concatD [prt 7 expr1, doc (showString ".."), prt 7 expr2])
    ERangeExcl _ expr1 expr2 -> prPrec i 6 (concatD [prt 7 expr1, doc (showString "..."), prt 7 expr2])
    ERangeInf _ expr -> prPrec i 6 (concatD [prt 7 expr, doc (showString "...")])
    ECmp _ cmp -> prPrec i 5 (concatD [prt 0 cmp])
    ENot _ expr -> prPrec i 5 (concatD [doc (showString "not"), prt 5 expr])
    EAnd _ expr1 expr2 -> prPrec i 4 (concatD [prt 5 expr1, doc (showString "and"), prt 4 expr2])
    EOr _ expr1 expr2 -> prPrec i 3 (concatD [prt 4 expr1, doc (showString "or"), prt 3 expr2])
    ETuple _ exprs -> prPrec i 1 (concatD [prt 3 exprs])
    ECond _ expr1 expr2 expr3 -> prPrec i 2 (concatD [prt 3 expr1, doc (showString "?"), prt 3 expr2, doc (showString ":"), prt 2 expr3])
    ELambda _ ids expr -> prPrec i 2 (concatD [doc (showString "lambda"), prt 0 ids, doc (showString "->"), prt 2 expr])
  prtList 3 [x] = concatD [prt 3 x]
  prtList 3 (x:xs) = concatD [prt 3 x, doc (showString ","), prt 3 xs]
  prtList 2 [] = concatD []
  prtList 2 [x] = concatD [prt 2 x]
  prtList 2 (x:xs) = concatD [prt 2 x, doc (showString ","), prt 2 xs]
  prtList _ [x] = concatD [prt 0 x]
  prtList _ (x:xs) = concatD [prt 0 x, doc (showString "="), prt 0 xs]

instance Print (Type a) where
  prt i e = case e of
    TPtr _ type_ -> prPrec i 4 (concatD [prt 4 type_])
    TArr _ n type_ -> prPrec i 4 (concatD [prt 0 n, prt 4 type_])
    TDeref _ type_ -> prPrec i 4 (concatD [prt 4 type_])
    TLabel _ -> prPrec i 4 (concatD [doc (showString "Label")])
    TVoid _ -> prPrec i 4 (concatD [doc (showString "Void")])
    TInt _ -> prPrec i 4 (concatD [doc (showString "Int")])
    TBool _ -> prPrec i 4 (concatD [doc (showString "Bool")])
    TChar _ -> prPrec i 4 (concatD [doc (showString "Char")])
    TObject _ -> prPrec i 4 (concatD [doc (showString "Object")])
    TString _ -> prPrec i 4 (concatD [doc (showString "String")])
    TArray _ type_ -> prPrec i 4 (concatD [doc (showString "["), prt 0 type_, doc (showString "]")])
    TTuple _ types -> prPrec i 2 (concatD [prt 3 types])
    TArgN _ type_ id -> prPrec i 2 (concatD [prt 1 type_, prt 0 id])
    TArgD _ type_ id str -> prPrec i 2 (concatD [prt 1 type_, prt 0 id, prt 0 str])
    TFunc _ types type_ -> prPrec i 1 (concatD [prt 2 types, doc (showString "->"), prt 1 type_])
  prtList 3 [x] = concatD [prt 3 x]
  prtList 3 (x:xs) = concatD [prt 3 x, doc (showString "*"), prt 3 xs]
  prtList 2 [] = concatD []
  prtList 2 [x] = concatD [prt 2 x]
  prtList 2 (x:xs) = concatD [prt 2 x, doc (showString ","), prt 2 xs]

