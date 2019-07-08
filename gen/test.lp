% gen.lp
%
% Core generation rules.


#const max_lines = 6.
#const min_lines = 2.

% List of line ID values:
line_id(1..max_lines).

% Pick a line count:
1 = { line_count(X): line_id(X), X >= min_lines }.

% Basic components

%variable(ay; zed; uwu).
%constant(1; 2; 5; 11).
%constant(1; 2; 3; 5; 7; 11).

variable(ay; zed; uwu).
constant(_const_).

% Operators

% TODO: Abstract over operators!
%unop(neg; nt).
%binop(plus; minus; times; divide; intdiv; modulo; exp; compare; and; or).
%asgop(plus; minus; times; divide; intdiv; modulo; exp).

unop(_unop_).
binop(_binop_).
asgop(_asgop_).

% Dependencies

line_depends(Line, Var) :-
  code_line(Line, Expr),
  depends(Expr, Var).

depends(Var, Var) :- variable(Var).

% Updates

updates(Var, Var) :- variable(Var).

line_updates(Line, Var) :-
  code_line(Line, Expr),
  updates(Expr, Var).

% Core rules

error("Unmet dependency") :-
  line_depends(Line, Var),
  0 = {
    line_updates(Prev, Var): Prev < Line
  }.
% vars.lp
%
% Rules for generating simple variable + assignment puzzles.


% Generation rules:

% One assignment expression per line:
1 = { code_line(Line, Expr): any_asg(Expr) } :- line_id(Line).

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
  depends(B, Var).

% Updates

updates(assign(A, B), Var) :- any_asg(assign(A, B)), updates(A, Var).
updates(augassign(Op, A, B), Var) :-
  any_asg(augassign(Op, A, B)),
  updates(A, Var).
