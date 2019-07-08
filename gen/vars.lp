% vars.lp
%
% Rules for generating simple variable + assignment puzzles.

#program vars.

% Generation rules:

% One assignment expression per line:
1 = { code_line(Line, Expr): any_asg(Expr) } :- using_line(Line).

expr_on_line(Line, Expr) :- code_line(Line, Expr).
expr_on_line(Line, Sub) :- expr_on_line(Line, unop(Op, Sub)).
expr_on_line(Line, SubL) :- expr_on_line(Line, binop(Op, SubL, SubR)).
expr_on_line(Line, SubR) :- expr_on_line(Line, binop(Op, SubL, SubR)).
expr_on_line(Line, Var) :- expr_on_line(Line, assign(Var, Val)).
expr_on_line(Line, Val) :- expr_on_line(Line, assign(Var, Val)).
expr_on_line(Line, Var) :- expr_on_line(Line, augassign(Op, Var, Val)).
expr_on_line(Line, Val) :- expr_on_line(Line, augassign(Op, Var, Val)).

error(m("Stacked unary operators.")) :-
  expr_on_line(Line, unop(Op, unop(Oop, Expr))).

error(m("Redundant assignment.")) :-
  expr_on_line(Line, assign(Var, Var)).

error(m("Update of unused value.")) :-
  line_updates(First, Var),
  line_updates(Later, Var),
  Later > First,
  0 = { line_depends(Between, Var) : First < Between, Between < Later },
  0 = { line_depends(Later, Var) }.

error(m("Pointless math.", Line)) :-
  expr_on_line(Line, binop(Op, _const_, _const_)).

error(m("Pointless math.", Line)) :-
  expr_on_line(Line, binop(Op, unop(OpA, _const_), _const_)).

error(m("Pointless math.", Line)) :-
  expr_on_line(Line, binop(Op, _const_, unop(OpA, _const_))).

error(m("Pointless math.", Line)) :-
  expr_on_line(Line, binop(Op, unop(OpA, _const_), unop(OpB, _const_))).

error(m("Var on both sides.", Line)) :-
  expr_on_line(Line, binop(Op, Var, Var)),
  variable(Var).

error(m("Var on both sides.", Line)) :-
  expr_on_line(Line, binop(Op, unop(OpA, Var), Var)),
  variable(Var).

error(m("Var on both sides.", Line)) :-
  expr_on_line(Line, binop(Op, Var, unop(OpB, Var))),
  variable(Var).

error(m("Var on both sides.", Line)) :-
  expr_on_line(Line, binop(Op, unop(OpA, Var), unop(OpB, Var))),
  variable(Var).

head_line(Line, Var) :-
  code_line(Line, Expr),
  line_updates(Line, Var),
  0 = { line_depends(Line, Var) : variable(Var) }.

pure_head(Line) :-
  head_line(Line, SomeVar),
  0 = { body_line(Line, Var) : variable(Var) }.

body_line(Line, Var) :-
  code_line(Line, Expr),
  line_depends(Line, Var).

error(m("Too many pure assignemnts.")) :-
  3 <= { pure_head(Line) : using_line(Line) }.

pure_co_update_test(Fourth) :-
  line_updates(First, VarA),
  line_updates(Second, VarB),
  line_depends(Second, VarA),
  line_updates(Third, VarA),
  0 = { line_depends(Third, VarB) },
  line_depends(Fourth, VarB),
  0 = { line_depends(Fourth, VarA) },
  First < Second,
  Second < Third,
  Third < Fourth.

error(m("No pure co-update test.")) :-
  0 = { pure_co_update_test(L) : using_line(L) }.

co_update_test(Fourth) :-
  line_updates(First, VarA),
  line_updates(Second, VarB),
  line_depends(Second, VarA),
  line_updates(Third, VarA),
  line_depends(Fourth, VarB),
  0 = { line_depends(Fourth, VarA) },
  First < Second,
  Second < Third,
  Third < Fourth.

error(m("No co-update test.")) :-
  0 = { co_update_test(L) : using_line(L) }.

% Allowable expressions

expr_depth(0; 1; 2).

expr(X, 0) :- variable(X).
expr(X, 0) :- constant(X).
expr(unop(OP, A), 1) :- unop(OP), expr(A, 0).
expr(unop(OP, A), 2) :- unop(OP), expr(A, 1).
expr(binop(OP, A, B), 1) :- binop(OP), expr(A, 0), expr(B, 0).
expr(binop(OP, A, B), 2) :- binop(OP), expr(A, 1), expr(B, 0).
expr(binop(OP, A, B), 2) :- binop(OP), expr(A, 0), expr(B, 1).
expr(binop(OP, A, B), 2) :- binop(OP), expr(A, 1), expr(B, 1).
% TODO: dot and index?
asg_expr(assign(Var, Val), 0) :- variable(Var), expr(Val, 0).
asg_expr(assign(Var, Val), 1) :- variable(Var), expr(Val, 1).
asg_expr(assign(Var, Val), 2) :- variable(Var), expr(Val, 2).
asg_expr(augassign(Op, Var, Val), 0) :- asgop(Op), variable(Var), expr(Val, 0).
asg_expr(augassign(Op, Var, Val), 1) :- asgop(Op), variable(Var), expr(Val, 1).
asg_expr(augassign(Op, Var, Val), 2) :- asgop(Op), variable(Var), expr(Val, 2).

any_expr(X) :- expr(X, N).
any_asg(X) :- asg_expr(X, N).

% Dependencies

depends(binop(Op, A, B), Var) :- any_expr(binop(Op, A, B)), depends(A, Var).
depends(binop(Op, A, B), Var) :- any_expr(binop(Op, A, B)), depends(B, Var).
depends(unop(Op, A), Var) :- any_expr(unop(Op, A)), depends(A, Var).
depends(assign(A, B), Var) :- any_asg(assign(A, B)), depends(B, Var).
depends(augassign(Op, A, B), Var) :-
  any_asg(augassign(Op, A, B)),
  depends(A, Var).
depends(augassign(Op, A, B), Var) :-
  any_asg(augassign(Op, A, B)),
  depends(B, Var).

% Updates

updates(assign(A, B), Var) :- any_asg(assign(A, B)), updates(A, Var).
updates(augassign(Op, A, B), Var) :-
  any_asg(augassign(Op, A, B)),
  updates(A, Var).
