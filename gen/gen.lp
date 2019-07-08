% gen.lp
%
% Core generation rules.

#program gen.

#const max_lines = 3.
#const min_lines = 2.

% List of line ID values:
line_id(1..max_lines).

% Pick a line count:
1 = { line_count(X): line_id(X), X >= min_lines }.

% Basic components

%variable(ay; zed; uwu).
%constant(1; 2; 5; 11).
%constant(1; 2; 3; 5; 7; 11).

variable(_var_).
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
