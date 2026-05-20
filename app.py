from flask import Flask, request, jsonify
import ast
import operator

app = Flask(__name__)

# Supported arithmetic operators
OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

def safe_eval(node):
    """
    Recursively evaluate abstract syntax tree nodes safely.
    Only allows basic arithmetic operations and numeric constants.
    """
    if isinstance(node, ast.Expression):
        return safe_eval(node.body)
    
    elif isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float)):
            raise ValueError("Only numeric constants are allowed.")
        return node.value
    
    elif isinstance(node, ast.Num):  # Fallback for Python versions < 3.8
        return node.n
    
    elif isinstance(node, ast.BinOp):
        left = safe_eval(node.left)
        right = safe_eval(node.right)
        op_type = type(node.op)
        
        if op_type in OPERATORS:
            # Handle division by zero explicitly
            if op_type in (ast.Div, ast.FloorDiv) and right == 0:
                raise ZeroDivisionError("Division by zero is not allowed.")
            
            # Prevent potential denial of service from extremely large power calculations
            if op_type == ast.Pow:
                if abs(left) > 10000 or abs(right) > 1000:
                    raise ValueError("Power operation arguments are too large.")
            
            return OPERATORS[op_type](left, right)
        
        raise ValueError(f"Unsupported binary operator: {op_type.__name__}")
    
    elif isinstance(node, ast.UnaryOp):
        operand = safe_eval(node.operand)
        op_type = type(node.op)
        
        if op_type in OPERATORS:
            return OPERATORS[op_type](operand)
        
        raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
    
    else:
        raise ValueError(f"Unsupported expression component: {type(node).__name__}")

def evaluate_expression(expression: str) -> int:
    """
    Parse the expression and evaluate it safely to return an integer result.
    """
    if not expression or not isinstance(expression, str):
        raise ValueError("Expression must be a non-empty string.")
    
    clean_expr = expression.strip()
    if not clean_expr:
        raise ValueError("Expression cannot be empty.")
    
    # Parse the expression safely into an AST expression node
    tree = ast.parse(clean_expr, mode='eval')
    result = safe_eval(tree)
    
    if isinstance(result, (int, float)):
        return int(result)
        
    raise ValueError("Result of expression is not a numeric value.")

@app.route('/calculate', methods=['GET', 'POST'])
def calculate():
    """
    API endpoint that accepts basic arithmetic expressions and returns the result.
    GET: Expects ?expression=2+2
    POST: Expects JSON {"expression": "2+2"} or form data
    """
    expression = None

    if request.method == 'POST':
        if request.is_json:
            data = request.get_json() or {}
            expression = data.get('expression')
        else:
            expression = request.form.get('expression')
    else:  # GET
        expression = request.args.get('expression')

    if not expression:
        return jsonify({"error": "Missing expression parameter"}), 400

    try:
        result = evaluate_expression(expression)
        return jsonify({"result": result})
    except ZeroDivisionError as e:
        return jsonify({"error": str(e)}), 400
    except (SyntaxError, ValueError) as e:
        return jsonify({"error": f"Invalid expression: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
