from intbase import InterpreterBase
from intbase import ErrorType
import re

class Interpreter(InterpreterBase):
    operators = ["+", "-", "*", "/", "%", "<", ">", "<=", ">=", "!=", "==", "&", "|"]

    def __init__(self, console_output = True, input = None, trace_output = False):
        super().__init__(console_output, input)
        self.program_statements_ = []
        self.ip_ = 0
        self.terminated_ = True
        self.var_dict_ = {} # dictionary for variables to values 
        self.func_dict_ = {} # function name to line number 
        self.result_ = None # put result in the variable dict 
        self.funccall_stack_ = [] # stack for funccalls
        self.while_stack_ = [] # stack for while loops

    def reset_all_variables(self):
        self.program_statements_ = []
        self.ip_ = 0
        self.terminated_ = True
        self.var_dict_ = {} 
        self.func_dict_ = {} 
        self.result_ = None

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

    def jump(self, index):
        self.ip_ = index
        return self.ip_

    def jump_from_return(self, index):
        self.ip_ = index-1
        return self.ip_

    def check_if_int(self, s):
        if (s[0] == '-'):
            s = s[1:]
        if (s.isnumeric()):
            return True
        return False

    def check_type(self, s):
        if (s in self.var_dict_):
            s = self.var_dict_[s]
        if (isinstance(s, int)):
            return self.INT_DEF
        elif (self.check_if_int(s)):
            return self.INT_DEF
        elif (s == 'True' or s == 'False'):
            return self.BOOL_DEF
        elif (s[0] == '"'):
            return self.STRING_DEF
        else:
            return None

    def funccall_user_def(self, p):
        func_name = p[1]
        if (func_name not in self.func_dict_):
            super().error(ErrorType.NAME_ERROR, line_num = self.ip_)
        else:
            func_index = self.func_dict_[func_name]
            self.funccall_stack_.append(self.ip_+1)
            self.ip_ = self.jump(func_index)

    def funccall_def(self, p):
        output = ""
        if (p[1] == self.PRINT_DEF):
            for token in p[2:]:
                if (token in self.var_dict_): # variable 
                    if (isinstance(self.var_dict_[token], str)):
                        output += self.var_dict_[token].strip('\"')
                    else: 
                        output += str(self.var_dict_[token])
                elif (token == "result"): # result 
                    if (self.result_ == None):
                        super().error(ErrorType.NAME_ERROR, line_num = self.ip_)
                    if (isinstance(self.result_, str)):
                        output += self.result_.strip('\"')
                    else: 
                        output += str(self.result_)
                elif (self.check_type(token) != self.INT_DEF and self.check_type(token) != self.STRING_DEF and self.check_type(token) != self.BOOL_DEF):
                    super().error(ErrorType.NAME_ERROR, line_num = self.ip_)
                else:
                    output += token.strip('\"')
            super().output(output) 

        elif (p[1] == self.STRTOINT_DEF):
            if (p[2] in self.var_dict_):
                if (self.check_type(self.var_dict_[p[2]]) == self.STRING_DEF):
                    self.result_ = int(self.var_dict_[p[2]].strip('\"'))
                else:
                    super().error(ErrorType.TYPE_ERROR, line_num = self.ip_)
            elif (p[2] == "result"):
                if (self.result_[0] == '"'):
                    self.result_ = int(self.result_.strip('\"'))
                else:
                    super().error(ErrorType.TYPE_ERROR, line_num = self.ip_)
            else:
                if (p[2][0] == '"'):
                    self.result_ = int(p[2].strip('\"'))
                else:
                    super().error(ErrorType.TYPE_ERROR, line_num = self.ip_)

        elif (p[1] == self.INPUT_DEF):
            for token in p[2:]:
                if (token in self.var_dict_):
                    if (isinstance(self.var_dict_[token], str)):
                        output += self.var_dict_[token].strip('\"')
                    else:
                        output += str(self.var_dict_[token])
                elif (self.check_type(token) != self.INT_DEF and self.check_type(token) != self.STRING_DEF and self.check_type(token) != self.BOOL_DEF):
                    super().error(ErrorType.NAME_ERROR, line_num = self.ip_)
                else:
                    if (isinstance(token, str)):
                        output += token.strip('\"')
                    else:
                        output += str(token)
            super().output(output) 
            res = super().get_input()
            self.result_ = '"' + res + '"'

        else:  
            self.funccall_user_def(p)

    def evaluate_string_exp(self, v1, v2, i):
        if (v1 in self.var_dict_):
            v1 = self.var_dict_[v1]
        if (v2 in self.var_dict_):
            v2 = self.var_dict_[v2]
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
        if (v1 in self.var_dict_):
            v1 = self.var_dict_[v1]
        if (v2 in self.var_dict_):
            v2 = self.var_dict_[v2]
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
        if (v1 in self.var_dict_):
            v1 = self.var_dict_[v1]
        if (v2 in self.var_dict_):
            v2 = self.var_dict_[v2]
        v1 = eval(v1)
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
                if (i == "result"):
                    i = self.result_
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
        if (p[0] == self.ASSIGN_DEF): 
            expression = p[2:]
            result = self.evaluate_expression(expression)
            if (p[1] == "result"):
                self.result_ = result
            else:
                self.var_dict_[p[1]] = result
        elif (p[0] == self.RETURN_DEF):
            expression = p[1:]
            result = self.evaluate_expression(expression)
            self.result_ = result

    def assign_def(self, p):
        if (p[2] == "result"):
            if (self.result_ == None):
                super().error(ErrorType.NAME_ERROR, line_num = self.ip_)
            self.var_dict_[p[1]] = self.result_
        elif (len(p) == 3 and p[1] == "result"):
            self.result_ = p[2]
        elif (p[2] in self.operators): # expression
            self.handle_operation(p)
        elif (p[2] in self.var_dict_): # defined variable 
            self.var_dict_[p[1]] = self.var_dict_[p[2]]
        else:
            type_ = self.check_type(p[2])
            if (type_ != self.INT_DEF and type_ != self.STRING_DEF and type_ != self.BOOL_DEF):
                super().error(ErrorType.NAME_ERROR, line_num = self.ip_)
            self.var_dict_[p[1]] = p[2]

    def locate_endwhile(self):
        while_count = 0
        endwhile_count = 0
        for index, p in enumerate(self.program_statements_[self.ip_+1:]): # go through program and find correspondinf while/endwhile 
            if (len(p) == 0):
                continue 
            elif (p[0] == "while"):
                while_count += 1
            elif (p[0] == "endwhile"):
                if (while_count == endwhile_count):
                    return self.ip_ + index + 1
                endwhile_count += 1

    def handle_while_loop(self):
        self.while_stack_.append(self.ip_)

    def while_def(self, p):
        expression = p[1:]
        if (len(expression) == 1): # constant passed in 
            if (self.check_type(p[1]) == None): # undefined variable
                super().error(ErrorType.NAME_ERROR, line_num = self.ip_)
            if (self.check_type(p[1]) != self.BOOL_DEF): # int or string passed in 
                super().error(ErrorType.TYPE_ERROR, line_num = self.ip_)
                return 
            else:
                result = eval(p[1])
        else:
            result = self.evaluate_expression(expression)
        if (result != True and result != False):
            super().error(ErrorType.TYPE_ERROR, line_num = self.ip_)
            return 
        if (result == True): # go into the while loop
            self.handle_while_loop()
            return 
        if (result == False): # condition was not met 
            self.ip_ = self.locate_endwhile()
            return 

    def endwhile_def(self):
        while_ip = self.while_stack_.pop() # retrieve corresponding while statement
        self.ip_ = self.jump_from_return(while_ip)

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
                    return self.ip_ + index + 1
                endif_count += 1

    def if_def(self, p):
        expression = p[1:]
        if (len(expression) == 1): # constant is passed in 
            if (self.check_type(p[1]) != self.BOOL_DEF): # int or string passed in 
                super().error(ErrorType.TYPE_ERROR, line_num = self.ip_)
                return 
            else: 
                if (p[1] in self.var_dict_):
                    result = eval(self.var_dict_[p[1]])
                else:
                    result = eval(p[1])
        else: 
            result = self.evaluate_expression(expression)
        if (result != True and result != False):
            super().error(ErrorType.TYPE_ERROR, line_num = self.ip_)
            return 
        if (result == True): # go into the if statement 
            return
        else: # if condition was not met 
            self.ip_ = self.locate_else_endif()
            return

    def else_def(self, p):
        self.ip_ = self.locate_else_endif()
        return

    def return_def(self, p):
        if (not self.funccall_stack_): # stack is empty 
            self.terminated_ = True
            return
        recent_ip = self.funccall_stack_.pop()
        if (len(p) == 1): # 'return' statement
            self.ip_ = self.jump_from_return(recent_ip)
        elif (p[1] in self.operators): # return statement with expression
            self.handle_operation(p)
            self.ip_ = self.jump_from_return(recent_ip)
        elif (p[1] == "result"): # return result 
            self.result_ = self.result_
            self.ip_ = self.jump_from_return(recent_ip)
        elif (p[1] in self.var_dict_):
            self.result_ = self.var_dict_[p[1]]
            self.ip_ = self.jump_from_return(recent_ip)
        else:
            self.result_ = p[1]
            self.ip_ = self.jump_from_return(recent_ip)

    def endfunc_def(self):
        if (self.funccall_stack_):
            recent_ip = self.funccall_stack_.pop()
            self.ip_ = self.jump_from_return(recent_ip)
        else:
            self.terminated_ = True 
                
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

            elif (p[0] == self.RETURN_DEF): # return statement
                self.return_def(p)

            elif (p[0] == self.ENDFUNC_DEF): # end of function
                self.endfunc_def()

        new_ip = self.ip_ + 1
        return new_ip

    def locate_main(self):
        self.ip_ = self.func_dict_["main"]
        return self.ip_

    # program is an array of strings 
    def run(self, program):
        self.reset_all_variables()
        self.program_statements_ = self.tokenize(program)
        self.ip_ = self.locate_main()
        self.func_dict_["main"] = self.ip_
        self.terminated_ = False

        while (not self.terminated_):
            self.ip_ = self.interpret_statement()
