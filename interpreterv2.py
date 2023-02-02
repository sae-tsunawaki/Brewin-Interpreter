from intbase import InterpreterBase
from intbase import ErrorType
import re

class Interpreter(InterpreterBase):
    operators = ["+", "-", "*", "/", "%", "<", ">", "<=", ">=", "!=", "==", "&", "|"]
    param_def_ = ["int", "string", "bool"]
    param_ref_def_ = ["refint", "refstring", "refbool"]
    return_def_ = ["int", "string", "bool", "void"]

    def __init__(self, console_output = True, input = None, trace_output = False):
        super().__init__(console_output, input)
        self.program_statements_ = []
        self.ip_ = 0
        self.terminated_ = True
        self.resulti_ = None # integer result
        self.resultb_ = None # boolean result
        self.results_ = None # string result
        self.func_dict_ = {} # func name to line number 
        self.funccall_stack_ = [] # stack for funccalls (store ip and func name)
        self.while_stack_ = [] # stack for while loops
        self.return_type_stack_ = [] # stack for return types 
        self.current_func_ = None # current function name 
        self.scope_stack_ = []

    def index_of_func(self, func_name):
        for index, elem in reversed(list(enumerate(self.scope_stack_))):
            if (elem[0] == func_name):
                return index
        return

    def get_current_scope(self):
        ind = self.index_of_func(self.current_func_)
        return len(self.scope_stack_[ind][1])-1 # retrieve the curent scope of this function

    def is_in_scope(self, var):
        scope = self.get_current_scope()
        ind = self.index_of_func(self.current_func_)
        while (scope != -1):
            if (var in self.scope_stack_[ind][1][scope]):
                return True
            scope -= 1
        return False

    def get_scope(self, var):
        scope = self.get_current_scope()
        ind = self.index_of_func(self.current_func_)
        while (scope != -1):
            if (var in self.scope_stack_[ind][1][scope]):
                return scope
            scope -= 1
        return 

    def filter_out_comments(self, p):
        if (p[0] != '"'): # comment directly follows a var or int 
            return p.index("#")
        else: # comment directly follows a string 
            double_quote_count = p.count('"') # count the number of double quotes 
            if (double_quote_count == 2):
                if (p[len(p)-1] == '"'): # if == 2 and ends with ", it is just a string expression
                    return len(p)
                quote_end_index = p.find('"', 1)
                ind_to_slice = p.find('#', quote_end_index)
                return ind_to_slice
            else:
                return p.index("#")

    def tokenize(self, program):
        for ind, p in enumerate(program):
            split_p = re.split('[ ](?=(?:[^"]*"[^"]*")*[^"]*$)', p.strip())
            split_p = [i for i in split_p if i]
            for index, elem in enumerate(split_p): # get rid of comments in same line as code 
                if (elem != ""):
                    if (elem == "#" or elem[0] == "#"): 
                        split_p = split_p[:index]
                        continue 
                    elif ("#" in elem): # '#' is somewhere 
                        comment_index = self.filter_out_comments(elem)
                        if (comment_index == len(elem)): # the elem is valid so move on to the next one 
                            continue 
                        new_elem = elem[:comment_index]
                        split_p = split_p[:index]
                        split_p.append(new_elem)
            if (len(split_p) > 0):
                if (split_p[0] == "func"):
                    self.func_dict_[split_p[1]] = ind
            self.program_statements_.append(split_p)
        return self.program_statements_

    def func_def(self, p):
        if (p[1] == "main"):
            return 
        else: 
            self.func_dict_[p[1]] = self.ip_

    def jump_from_return(self, index):
        if (index == 0):
            return 0
        self.ip_ = index-1
        return self.ip_

    def check_if_int(self, s):
        if (s[0] == '-'):
            s = s[1:]
        if (s.isnumeric()):
            return True
        return False

    def check_type(self, s):
        if (isinstance(s, bool)):
            return self.BOOL_DEF
        elif (s == 'True' or s == 'False'):
            return self.BOOL_DEF
        elif (isinstance(s, int)):
            return self.INT_DEF
        elif (self.check_if_int(s)):
            return self.INT_DEF
        elif (s[0] == '"'):
            return self.STRING_DEF
        elif (self.is_in_scope(s)):
            scope = self.get_scope(s)
            var = self.scope_stack_[-1][1][scope][s]
            return var[1]
        else:
            super().error(ErrorType.NAME_ERROR, line_num = self.ip_)

    def check_func_def(self, func_def, func_call):
        return_type_ = func_def[len(func_def)-1] # extract return type 
        if (return_type_ not in self.return_def_): # invalid return type 
            super().error(ErrorType.NAME_ERROR, line_num = self.ip_)
        if (len(func_def)-len(func_call) != 1): # num of parameters do not match 
            super().error(ErrorType.NAME_ERROR, line_num = self.ip_)
        def_param_ = []
        for index, parameter in enumerate(func_def[2:-1]): # traverse through parameters
            param_def = parameter.split(":")
            if (param_def[0] in def_param_):
                super().error(ErrorType.NAME_ERROR, line_num = self.ip_)
            else:
                def_param_.append(param_def[0])

    def check_param_type(self, a, b):
        if (a not in self.param_def_ and a not in self.param_ref_def_): # invalid parameter name 
            super().error(ErrorType.NAME_ERROR, line_num = self.ip_)
        if (b not in self.param_def_ and b not in self.param_ref_def_): # invalid parameter name 
            super().error(ErrorType.NAME_ERROR, line_num = self.ip_)
        if (a == b):
            return 
        if (a[0:3] == "ref"):
            if (a[3:] == b):
                return 
        if (b[0:3] == "ref"):
            if (b[3:] == a):
                return
        super().error(ErrorType.TYPE_ERROR, line_num = self.ip_)

    def parse_func_def(self, func_def, func_call):
        self.check_func_def(func_def, func_call)
        if (len(func_def) == 3): # no parameters, only return type
            self.return_type_stack_.append(func_def[2])
            this_func = func_def[1]
            self.scope_stack_.append([this_func, []]) # create new stack entry for this func
            self.scope_stack_[-1][1].append({}) # create var dict for this func
            return 
        self.return_type_stack_.append(func_def[len(func_def)-1]) # extract return type 

        arg_def = []
        for arg in func_call[2:]: # extract arg from caller & check if valid 
            if (self.is_in_scope(arg)):
                scope = self.get_scope(arg)
                ind = self.index_of_func(self.current_func_)
                arg_def.append(self.scope_stack_[ind][1][scope][arg])
            else: # a constant is passed in 
                arg_def.append([arg, self.check_type(arg)])
        this_func = func_def[1]
        self.scope_stack_.append([this_func, []]) # create new stack entry for this func
        self.scope_stack_[-1][1].append({}) # create var dict for this func
        ind = self.index_of_func(this_func)
        for index, parameter in enumerate(func_def[2:-1]): # traverse through parameters
            param_def = parameter.split(":")
            self.check_param_type(param_def[1], arg_def[index][1]) # check if the parameter types are valid/if they match
        
            if (param_def[1] in self.param_def_): # pass by value  
                self.scope_stack_[ind][1][0][param_def[0]] = [arg_def[index][0], arg_def[index][1]]

            elif (param_def[1] in self.param_ref_def_): # pass by reference 
                self.scope_stack_[ind][1][0][param_def[0]] = arg_def[index] 

    def funccall_user_def(self, p):
        func_name = p[1]
        if (func_name not in self.func_dict_):
            super().error(ErrorType.NAME_ERROR, line_num = self.ip_)
        else:
            func_index = self.func_dict_[func_name]
            func_def_ = self.program_statements_[func_index]
            self.funccall_stack_.append([self.ip_+1, self.current_func_])
            self.parse_func_def(func_def_, p)
            self.ip_ = self.jump_from_return(func_index)
            self.current_func_ = func_name # change func name for the dict 

    def funccall_def(self, p):
        output = ""
        if (p[1] == self.PRINT_DEF):
            for token in p[2:]:
                if (self.is_in_scope(token)): # token is in scope 
                    scope = self.get_scope(token)
                    var_scope = self.scope_stack_[-1][1][scope]
                    if (var_scope[token][1] == self.STRING_DEF):
                        output += var_scope[token][0].strip('\"')
                    else: 
                        output += str(var_scope[token][0])
                elif (self.check_type(token) != self.INT_DEF and self.check_type(token) != self.STRING_DEF and self.check_type(token) != self.BOOL_DEF):
                    super().error(ErrorType.NAME_ERROR, line_num = self.ip_)
                else:
                    output += token.strip('\"')
            super().output(output) 

        elif (p[1] == self.STRTOINT_DEF):
            if (self.is_in_scope(p[2])):
                scope = self.get_scope(p[2])
                var_scope = self.scope_stack_[-1][1][scope]
                if (var_scope[p[2]][1] == self.STRING_DEF):
                    self.resulti_ = int(var_scope[p[2]][0].strip('\"'))
                    self.scope_stack_[-1][1][0]["resulti"] = [self.resulti_, self.INT_DEF] # add to current func
                    if (self.funccall_stack_): # add to caller func
                        func_name = self.funccall_stack_[-1][1]
                        ind = self.index_of_func(func_name)
                        self.scope_stack_[ind][1][0]["resulti"] = [self.resulti_, self.INT_DEF]     
                else:
                    super().error(ErrorType.TYPE_ERROR, line_num = self.ip_)
            else:
                if (p[2][0] == '"'):
                    self.resulti_ = int(p[2].strip('\"'))
                    self.scope_stack_[-1][1][0]["resulti"] = [self.resulti_, self.INT_DEF] # add to current func
                    if (self.funccall_stack_): # add to caller func
                        func_name = self.funccall_stack_[-1][1]
                        ind = self.index_of_func(func_name)
                        self.scope_stack_[ind][1][0]["resulti"] = [self.resulti_, self.INT_DEF] 
                else:
                    super().error(ErrorType.TYPE_ERROR, line_num = self.ip_)

        elif (p[1] == self.INPUT_DEF):
            for token in p[2:]:
                if (self.is_in_scope(token)): # token is in scope 
                    scope = self.get_scope(token)
                    var_scope = self.scope_stack_[-1][1][scope]
                    if (var_scope[token][1] == self.STRING_DEF):
                        output += var_scope[token][0].strip('\"')
                    else: 
                        output += str(var_scope[token][0])
                elif (self.check_type(token) != self.INT_DEF and self.check_type(token) != self.STRING_DEF and self.check_type(token) != self.BOOL_DEF):
                    super().error(ErrorType.NAME_ERROR, line_num = self.ip_)
                else:
                    if (isinstance(token, str)):
                        output += token.strip('\"')
                    else:
                        output += str(token)
            super().output(output) 
            res = super().get_input()
            self.results_ = '"' + res + '"'
            self.scope_stack_[-1][1][0]["results"] = [self.results_, self.STRING_DEF] # add to current func
            if (self.funccall_stack_): # add to caller func
                func_name = self.funccall_stack_[-1][1]
                ind = self.index_of_func(func_name)
                self.scope_stack_[ind][1][0]["results"] = [self.results_, self.STRING_DEF]     

        else:  
            self.funccall_user_def(p)

    def evaluate_string_exp(self, v1, v2, i):
        if (self.is_in_scope(v1)):
            scope_v1 = self.get_scope(v1)
            v1 =  self.scope_stack_[-1][1][scope_v1][v1][0]
        if (self.is_in_scope(v2)):
            scope_v2 = self.get_scope(v2)
            v2 =  self.scope_stack_[-1][1][scope_v2][v2][0]
        v1 = v1.strip('\"')
        v2 = v2.strip('\"')
        if (i == '+'):
            return v1 + v2
        elif (i == '<'):
            return v1 < v2
        elif (i == '>'):
            return v1 > v2
        elif (i == '<='):
            return v1 <= v2
        elif (i == '>='):
            return v1 >= v2
        elif (i == '!='):
            return v1 != v2
        elif (i == '=='):
            return v1 == v2
        else:
            super().error(ErrorType.TYPE_ERROR, line_num = self.ip_)

    def evaluate_int_exp(self, v1, v2, i):
        if (self.is_in_scope(v1)):
            scope_v1 = self.get_scope(v1)
            v1 =  self.scope_stack_[-1][1][scope_v1][v1][0]
        if (self.is_in_scope(v2)):
            scope_v2 = self.get_scope(v2)
            v2 =  self.scope_stack_[-1][1][scope_v2][v2][0]
        v1 = int(v1)
        v2 = int(v2)
        if (i == '+'):
            return v1 + v2
        elif (i == '-'):
            return v1 - v2
        elif (i == '*'):
            return v1 * v2
        elif (i == '/'):
            return v1 // v2
        elif (i == '%'):
            return v1 % v2
        elif (i == '<'):
            return v1 < v2
        elif (i == '>'):
            return v1 > v2
        elif (i == '<='):
            return v1 <= v2
        elif (i == '>='):
            return v1 >= v2
        elif (i == '!='):
            return v1 != v2
        elif (i == '=='):
            return v1 == v2
        else:
            super().error(ErrorType.TYPE_ERROR, line_num = self.ip_)

    def evaluate_bool_exp(self, v1, v2, i): 
        if (self.is_in_scope(v1)):
            scope_v1 = self.get_scope(v1)
            v1 =  self.scope_stack_[-1][1][scope_v1][v1][0]
        if (self.is_in_scope(v2)):
            scope_v2 = self.get_scope(v2)
            v2 =  self.scope_stack_[-1][1][scope_v2][v2][0]
        if (v1 != True and v1 != False):
            v1 = eval(v1)
        if (v2 != True and v2 != False):
            v2 = eval(v2)
        if (i == '!='):
            return v1 != v2
        elif (i == '=='):
            return v1 == v2
        elif (i == '&'):
            return v1 & v2
        elif (i == '|'):
            return v1 | v2 
        else:
            super().error(ErrorType.TYPE_ERROR, line_num = self.ip_)

    def evaluate_expression(self, exp): # takes in expression list 
        stack = []
        for i in reversed(exp):
            if (i not in self.operators): # int, string, or var 
                stack.append(i)
            else:
                v1 = stack.pop()
                v2 = stack.pop()
                if (self.check_type(v1) != self.check_type(v2)): # types do not match
                    super().error(ErrorType.TYPE_ERROR, line_num = self.ip_)
                    return
                if (self.check_type(v1) == self.STRING_DEF):
                    result = self.evaluate_string_exp(v1, v2, i)
                    if (i == '+'):
                        result = '"' + result + '"'
                    stack.append(result)
                elif (self.check_type(v1) == self.INT_DEF):
                    stack.append(self.evaluate_int_exp(v1, v2, i))
                elif (self.check_type(v1) == self.BOOL_DEF):
                    stack.append(self.evaluate_bool_exp(v1, v2, i))
                elif (isinstance(v1, str)):
                    stack.append(self.evaluate_string_exp(v1, v2, i))
        return stack.pop()

    def handle_operation(self, p):
        expression = []
        if (p[0] == self.ASSIGN_DEF): # assign statement
            expression = p[2:]
            result = self.evaluate_expression(expression)
            if (self.is_in_scope(p[1])):
                scope = self.get_scope(p[1]) # get the scope of var we are assigning expression to 
            else:
                super().error(ErrorType.NAME_ERROR, line_num = self.ip_)
            if (self.scope_stack_[-1][1][scope][p[1]][1] != self.check_type(result)): # types of expression and var do not match
                super().error(ErrorType.TYPE_ERROR, line_num = self.ip_)
            else: 
                self.scope_stack_[-1][1][scope][p[1]][0] = result
        elif (p[0] == self.RETURN_DEF): # return statement 
            expression = p[1:]
            return self.evaluate_expression(expression)

    def assign_def(self, p):
        if (len(p) <= 2):
            super().error(ErrorType.NAME_ERROR, line_num = self.ip_)
        if (self.is_in_scope(p[1])): # var exists in outer scope 
            scope = self.get_scope(p[1]) # get the scope level of the var 
            scope_stack_1 = self.scope_stack_[-1][1][scope] # scope of p[1]
        else:
            super().error(ErrorType.NAME_ERROR, line_num = self.ip_)
        if (p[2] in self.operators): # expression 
            self.handle_operation(p)
        elif (self.is_in_scope(p[2])): # defined var assigned to another defined var 
            scope = self.get_scope(p[2]) # get the scope level of the var 
            scope_stack_2 = self.scope_stack_[-1][1][scope] # scope of p[2]
            if (self.check_type(p[1]) != self.check_type(p[2])):  
                super().error(ErrorType.TYPE_ERROR, line_num = self.ip_)
            else:
                scope_stack_1[p[1]][0] = scope_stack_2[p[2]][0]
        else: # defined var assigned to var 
            type_ = self.check_type(p[2])
            if (type_ != self.INT_DEF and type_ != self.STRING_DEF and type_ != self.BOOL_DEF):
                super().error(ErrorType.NAME_ERROR, line_num = self.ip_)
            elif (scope_stack_1[p[1]][1] == type_): # assign if the types match
                scope_stack_1[p[1]][0] = p[2]
            else:
                super().error(ErrorType.TYPE_ERROR, line_num = self.ip_)

    def locate_endwhile(self):
        while_count = 0
        endwhile_count = 0
        for index, p in enumerate(self.program_statements_[self.ip_+1:]): # go through program and find corresponding while/endwhile 
            if (len(p) == 0):
                continue 
            elif (p[0] == "while"):
                while_count += 1
            elif (p[0] == "endwhile"):
                if (while_count == endwhile_count):
                    return self.ip_ + index
                endwhile_count += 1

    def handle_while_loop(self):
        self.while_stack_.append(self.ip_)

    def while_def(self, p):
        expression = p[1:]
        scope = self.get_current_scope()
        scope_dict = self.scope_stack_[-1][1][scope]
        if (len(expression) == 1): # constant passed in 
            if (self.check_type(p[1]) != self.BOOL_DEF): # int or string passed in 
                super().error(ErrorType.TYPE_ERROR, line_num = self.ip_)
                return 
            else:
                if (p[1] in scope_dict):
                    if (scope_dict[p[1]][0] != True and scope_dict[p[1]][0] != False):
                        result = eval(scope_dict[p[1]][0])
                    else:
                        result = scope_dict[p[1]][0]
                else:
                    if (p[1] != True and p[1] != False):
                        result = eval(p[1])
                    else:
                        result = p[1]
        else:
            result = self.evaluate_expression(expression)
        if (self.check_type(result) != self.BOOL_DEF):
            super().error(ErrorType.TYPE_ERROR, line_num = self.ip_)
            return 
        if (result == True or result == "True"): # go into the while loop
            self.scope_stack_[-1][1].append({}) # create new scope for while
            self.handle_while_loop()
            return 
        if (result == False or result == "False"): # condition was not met 
            self.ip_ = self.locate_endwhile() + 1
            return 

    def endwhile_def(self):
        if (self.while_stack_):
            while_ip = self.while_stack_.pop() # retrieve corresponding while statement
            self.ip_ = self.jump_from_return(while_ip)
            self.scope_stack_[-1][1].pop()
            return

    def locate_else_endif(self):
        if_count = 0
        endif_count = 0
        for index, p in enumerate(self.program_statements_[self.ip_+1:]): # go through program and find corresponding else/endif
            if (len(p) == 0):
                continue
            elif (p[0] == "if"):
                if_count += 1
            elif (p[0] == "else"):
                if (if_count == endif_count):
                    return self.ip_ + index + 1
            elif (p[0] == "endif"):
                if (if_count == endif_count): # we found the matching endif
                    return self.ip_ + index 
                endif_count += 1

    def if_def(self, p):
        expression = p[1:]
        scope = self.get_current_scope()
        scope_dict = self.scope_stack_[-1][1][scope]
        if (len(expression) == 1): # constant is passed in 
            if (self.check_type(p[1]) != self.BOOL_DEF): # int or string passed in 
                super().error(ErrorType.TYPE_ERROR, line_num = self.ip_)
                return 
            else: 
                if (p[1] in scope_dict):
                    if (scope_dict[p[1]][0] != True and scope_dict[p[1]][0] != False):
                        result = eval(scope_dict[p[1]][0])
                    else:
                        result = scope_dict[p[1]][0]
                else:
                    if (p[1] != True and p[1] != False):
                        result = eval(p[1])
                    else:
                        result = p[1]

        else: # expression
            result = self.evaluate_expression(expression)
        if (self.check_type(result) != self.BOOL_DEF):
            super().error(ErrorType.TYPE_ERROR, line_num = self.ip_)
            return 
        if (result == True or result == "True"): # go into the if statement 
            self.scope_stack_[-1][1].append({}) # create new scope for if 
            return
        else: # if condition was not met 
            self.ip_ = self.locate_else_endif()
            self.scope_stack_[-1][1].append({}) # create new scope for else 
            return

    def else_def(self, p):
        self.ip_ = self.locate_else_endif()
        return

    def endif_def(self, p):
        self.scope_stack_[-1][1].pop()
        return

    def return_def(self, p):
        if (not self.funccall_stack_): # we are trying to return in main
            if (len(p) != 1): # not just a 'return'
                super().error(ErrorType.TYPE_ERROR, line_num = self.ip_)

        if (not self.funccall_stack_): # stack is empty 
            self.terminated_ = True
            return

        item = self.funccall_stack_.pop()
        recent_ip = item[0]
        caller_func = item[1]
        if (self.return_type_stack_): # not in main
            ret_type = self.return_type_stack_.pop()

        if (len(p) == 1): # 'return' statement
            self.ip_ = self.jump_from_return(recent_ip)
            if (ret_type != self.VOID_DEF): # return default values 
                if (ret_type == self.STRING_DEF):
                    self.results = ""
                    self.scope_stack_[-1][1][0]["results"] = ["", self.STRING_DEF]
                    self.scope_stack_[-2][1][0]["results"] = ["", self.STRING_DEF]
                elif (ret_type == self.INT_DEF):
                    self.resulti = 0
                    self.scope_stack_[-1][1][0]["resulti"] = [0, self.INT_DEF]
                    self.scope_stack_[-2][1][0]["resulti"] = [0, self.INT_DEF]
                elif (ret_type == self.BOOL_DEF):
                    self.resultb = "False"
                    self.scope_stack_[-1][1][0]["resultb"] = ["False", self.BOOL_DEF]
                    self.scope_stack_[-2][1][0]["resultb"] = ["False", self.BOOL_DEF]

        elif (p[1] in self.operators): # return statement with expression
            result = self.handle_operation(p)
            if (self.check_type(result) == ret_type):
                if (ret_type == self.STRING_DEF):
                    self.results = result
                    self.scope_stack_[-1][1][0]["results"] = [result, self.STRING_DEF]
                    self.scope_stack_[-2][1][0]["results"] = [result, self.STRING_DEF]
                elif (ret_type == self.INT_DEF):
                    self.resulti = result
                    self.scope_stack_[-1][1][0]["resulti"] = [result, self.INT_DEF]
                    self.scope_stack_[-2][1][0]["resulti"] = [result, self.INT_DEF]
                elif (ret_type == self.BOOL_DEF):
                    self.resultb = result
                    self.scope_stack_[-1][1][0]["resultb"] = [result, self.BOOL_DEF]
                    self.scope_stack_[-2][1][0]["resultb"] = [result, self.BOOL_DEF]
            else:
                super().error(ErrorType.TYPE_ERROR, line_num = self.ip_)
            self.ip_ = self.jump_from_return(recent_ip)

        elif (self.is_in_scope(p[1])): # return a variable 
            scope = self.get_scope(p[1])
            var = self.scope_stack_[-1][1][scope][p[1]]
            if (ret_type == var[1]): # types match 
                if (ret_type == self.STRING_DEF):
                    self.results = var[0]
                    self.scope_stack_[-1][1][0]["results"] = [var[0], self.STRING_DEF]
                    self.scope_stack_[-2][1][0]["results"] = [var[0], self.STRING_DEF]
                elif (ret_type == self.INT_DEF):
                    self.resulti = var[0]
                    self.scope_stack_[-1][1][0]["resulti"] = [var[0], self.INT_DEF]
                    self.scope_stack_[-2][1][0]["resulti"] = [var[0], self.INT_DEF]
                elif (ret_type == self.BOOL_DEF):
                    self.resultb = var[0]
                    self.scope_stack_[-1][1][0]["resultb"] = [var[0], self.BOOL_DEF]
                    self.scope_stack_[-2][1][0]["resultb"] = [var[0], self.BOOL_DEF]
            else:
                super().error(ErrorType.TYPE_ERROR, line_num = self.ip_)
            self.ip_ = self.jump_from_return(recent_ip)

        else: # return a constant 
            type_ = self.check_type(p[1])
            if (ret_type == type_): 
                if (ret_type == self.STRING_DEF):
                    self.results = p[1]
                    self.scope_stack_[-1][1][0]["results"] = [p[1], self.STRING_DEF]
                    self.scope_stack_[-2][1][0]["results"] = [p[1], self.STRING_DEF]
                elif (ret_type == self.INT_DEF):
                    self.resulti = p[1]
                    self.scope_stack_[-1][1][0]["resulti"] = [p[1], self.INT_DEF]
                    self.scope_stack_[-2][1][0]["resulti"] = [p[1], self.INT_DEF]
                elif (ret_type == self.BOOL_DEF):
                    self.resultb = p[1]
                    self.scope_stack_[-1][1][0]["resultb"] = [p[1], self.BOOL_DEF]
                    self.scope_stack_[-2][1][0]["resultb"] = [p[1], self.BOOL_DEF]
            else:
                super().error(ErrorType.TYPE_ERROR, line_num = self.ip_)
            self.ip_ = self.jump_from_return(recent_ip)

        self.scope_stack_.pop() # remove this func stack
        self.current_func_ = item[1]

    def endfunc_def(self):
        if (self.funccall_stack_):
            item = self.funccall_stack_.pop()
            recent_ip = item[0]
            caller_func = item[1]
            ind_caller_func = self.index_of_func(caller_func)
            line_num = self.func_dict_[self.current_func_] 
            line = self.program_statements_[line_num]
            ret_type = line[len(line)-1] # extract return type 
            if (ret_type == self.INT_DEF):
                if ("resulti" not in self.scope_stack_[-1][1]): # check if int was returned
                    self.scope_stack_[ind_caller_func][1][0]["resulti"] = [0, self.INT_DEF]
                    self.return_type_stack_.pop()

            elif (ret_type == self.STRING_DEF): # check if string was returned
                if ("results" not in self.scope_stack_[-1][1]):
                    self.scope_stack_[ind_caller_func][1][0]["results"] = ["", self.STRING_DEF]
                    self.return_type_stack_.pop()

            elif (ret_type == self.BOOL_DEF): # check if bool was returned
                if ("resultb" not in self.scope_stack_[-1][1]):
                    self.scope_stack_[ind_caller_func][1][0]["resultb"] = ["False", self.BOOL_DEF]
                    self.return_type_stack_.pop()

            else:
                self.return_type_stack_.pop()

            self.scope_stack_.pop() # remove this func stack
            self.current_func_ = item[1]
            self.ip_ = self.jump_from_return(recent_ip)
        else:
            self.terminated_ = True 

    def var_def(self, p):
        if (len(p) <= 2):
            super().error(ErrorType.NAME_ERROR, line_num = self.ip_)
        scope = self.get_current_scope() # retrive current env of this func 
        for var in p[2:]: # check for valid variable names 
            if (not var[0].isalpha()):
                super().error(ErrorType.NAME_ERROR, line_num = self.ip_)

        if (p[1] == self.INT_DEF):
            for var in p[2:]:
                if (self.is_in_scope(var)):
                    sc = self.get_scope(var)
                    if (scope == sc): # var exists in the same scope (redefinition)
                        super().error(ErrorType.NAME_ERROR, line_num = self.ip_)
                self.scope_stack_[-1][1][scope][var] = [0, self.INT_DEF]

        elif (p[1] == self.STRING_DEF):
            for var in p[2:]:
                if (self.is_in_scope(var)):
                    sc = self.get_scope(var)
                    if (scope == sc): # var exists in the same scope (redefinition)
                        super().error(ErrorType.NAME_ERROR, line_num = self.ip_)
                self.scope_stack_[-1][1][scope][var] = ["", self.STRING_DEF]

        elif (p[1] == self.BOOL_DEF):
            for var in p[2:]:
                if (self.is_in_scope(var)):
                    sc = self.get_scope(var)
                    if (scope == sc): # var exists in the same scope (redefinition)
                        super().error(ErrorType.NAME_ERROR, line_num = self.ip_)
                self.scope_stack_[-1][1][scope][var] = ["False", self.BOOL_DEF]

        else:
            super().error(ErrorType.TYPE_ERROR, line_num = self.ip_)
                
    def interpret_statement(self): 
        p = self.program_statements_[self.ip_]
        if (p != []): # not an empty line
            if (p[0] == self.FUNC_DEF): # either main or user defined function 
                self.func_def(p)
            
            elif (p[0] == self.FUNCCALL_DEF): # calling another function 
                self.funccall_def(p)

            elif (p[0] == self.ASSIGN_DEF): # assigning a variable to a value 
                self.assign_def(p)

            elif (p[0] == self.WHILE_DEF): # handle control flow 
                self.while_def(p)

            elif (p[0] == self.ENDWHILE_DEF): # end of control flow
                self.endwhile_def()

            elif (p[0] == self.IF_DEF): 
                self.if_def(p)

            elif (p[0] == self.ELSE_DEF): 
                self.else_def(p)

            elif (p[0] == self.ENDIF_DEF): 
                self.endif_def(p)

            elif (p[0] == self.RETURN_DEF): # return statement
                self.return_def(p)

            elif (p[0] == self.ENDFUNC_DEF): # end of function
                self.endfunc_def()

            elif (p[0] == self.VAR_DEF): # variable definition
                self.var_def(p)

        new_ip = self.ip_ + 1
        return new_ip

    def locate_main(self):
        self.ip_ = self.func_dict_["main"]
        return self.ip_

    # program is an array of strings 
    def run(self, program):
        self.program_statements_ = self.tokenize(program)
        self.ip_ = self.locate_main()
        self.func_dict_["main"] = self.ip_
        self.current_func_ = "main"
        self.scope_stack_.append([self.current_func_, []]) # create new stack entry for main
        self.scope_stack_[0][1].append({}) # create var dict for main
        self.terminated_ = False

        while (not self.terminated_):
            self.ip_ = self.interpret_statement()


