from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
import secrets
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# Gerar uma chave secreta adequada
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))

# Configuração do banco de dados
DATABASE = 'users.db'

def init_db():
    """Inicializa o banco de dados e cria a tabela de usuários"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # Inserir usuários padrão se a tabela estiver vazia
    cursor.execute('SELECT COUNT(*) FROM users')
    if cursor.fetchone()[0] == 0:
        default_users = [
            ('admin', generate_password_hash('password123')),
            ('user', generate_password_hash('hello123'))
        ]
        cursor.executemany('INSERT INTO users (username, password) VALUES (?, ?)', default_users)
    
    # Tabela de produtos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            image TEXT,
            units_per_box INTEGER NOT NULL,
            price DECIMAL(10,2),
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Inserir alguns produtos de exemplo se a tabela estiver vazia
    cursor.execute('SELECT COUNT(*) FROM products')
    if cursor.fetchone()[0] == 0:
        sample_products = [
            ('Arroz Integral', 'Grãos', 'arroz.jpg', 10, 12.50, 'Arroz integral de alta qualidade'),
            ('Feijão Preto', 'Grãos', 'feijao.jpg', 12, 8.90, 'Feijão preto selecionado'),
            ('Azeite de Oliva', 'Condimentos', 'azeite.jpg', 6, 25.90, 'Azeite extra virgem'),
            ('Macarrão Espaguete', 'Massas', 'macarrao.jpg', 8, 4.50, 'Macarrão espaguete tipo 1'),
            ('Açúcar Mascavo', 'Grãos', 'acucar.jpg', 15, 6.80, 'Açúcar mascavo orgânico'),
            ('Café em Grãos', 'Bebidas', 'cafe.jpg', 5, 18.90, 'Café em grãos premium'),
            ('Leite em Pó', 'Laticínios', 'leite.jpg', 8, 15.75, 'Leite em pó integral'),
            ('Farinha de Trigo', 'Grãos', 'farinha.jpg', 12, 5.20, 'Farinha de trigo especial')
        ]
        cursor.executemany(
            'INSERT INTO products (name, category, image, units_per_box, price, description) VALUES (?, ?, ?, ?, ?, ?)',
            sample_products
        )

    conn.commit()
    conn.close()

def get_db_connection():
    """Cria uma conexão com o banco de dados"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def get_user_by_username(username):
    """Busca um usuário pelo nome de usuário"""
    conn = get_db_connection()
    user = conn.execute(
        'SELECT * FROM users WHERE username = ?', (username,)
    ).fetchone()
    conn.close()
    return user

def create_user(username, password):
    """Cria um novo usuário no banco de dados"""
    try:
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO users (username, password) VALUES (?, ?)',
            (username, generate_password_hash(password))
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def get_all_products():
    """Busca todos os produtos do banco de dados"""
    conn = get_db_connection()
    products = conn.execute('''
        SELECT * FROM products ORDER BY name
    ''').fetchall()
    conn.close()
    return products

def get_product_by_id(product_id):
    """Busca um produto pelo ID"""
    conn = get_db_connection()
    product = conn.execute(
        'SELECT * FROM products WHERE id = ?', (product_id,)
    ).fetchone()
    conn.close()
    return product

def search_products_db(search_term=None, category=None):
    """Busca produtos no banco de dados com filtros"""
    conn = get_db_connection()
    
    query = 'SELECT * FROM products WHERE 1=1'
    params = []
    
    if search_term:
        query += ' AND (name LIKE ? OR category LIKE ? OR description LIKE ?)'
        params.extend([f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'])
    
    if category:
        query += ' AND category = ?'
        params.append(category)
    
    query += ' ORDER BY name'
    
    products = conn.execute(query, params).fetchall()
    conn.close()
    return products

def get_categories():
    """Busca todas as categorias disponíveis"""
    conn = get_db_connection()
    categories = conn.execute('''
        SELECT DISTINCT category FROM products ORDER BY category
    ''').fetchall()
    conn.close()
    return [cat['category'] for cat in categories]

def create_product(name, category, units_per_box, price=None, description=None, image=None):
    """Cria um novo produto no banco de dados"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO products (name, category, image, units_per_box, price, description)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, category, image, units_per_box, price, description))
        product_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return product_id
    except sqlite3.Error as e:
        print(f"Erro ao criar produto: {e}")
        return None

def update_product(product_id, name, category, units_per_box, price=None, description=None, image=None):
    """Atualiza um produto existente"""
    try:
        conn = get_db_connection()
        conn.execute('''
            UPDATE products 
            SET name = ?, category = ?, image = ?, units_per_box = ?, price = ?, description = ?
            WHERE id = ?
        ''', (name, category, image, units_per_box, price, description, product_id))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"Erro ao atualizar produto: {e}")
        return False

def delete_product(product_id):
    """Exclui um produto do banco de dados"""
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM products WHERE id = ?', (product_id,))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"Erro ao excluir produto: {e}")
        return False

@app.route('/')
def home():
    if 'username' in session:
        username = session['username']
        return f'Bem-vindo, {username}! {render_template("Inicio/inicio.html")}'
    return render_template('Home/home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        # Validar entrada
        if not username or not password:
            flash('Por favor, preencha todos os campos!', 'error')
            return render_template('Login/login.html')
        
        # Verificar credenciais no banco de dados
        user = get_user_by_username(username)
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Nome de usuário ou senha incorretos!', 'error')
    
    return render_template('Login/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validar entrada
        if not username or not password:
            flash('Por favor, preencha todos os campos!', 'error')
            return render_template('Register/register.html')
        
        if password != confirm_password:
            flash('As senhas não coincidem!', 'error')
            return render_template('Register/register.html')
        
        if len(password) < 6:
            flash('A senha deve ter pelo menos 6 caracteres!', 'error')
            return render_template('Register/register.html')
        
        # Criar novo usuário
        if create_user(username, password):
            flash('Registro realizado com sucesso! Faça login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Nome de usuário já existe!', 'error')
    
    return render_template('Register/register.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('home'))

# ========== ROTAS PARA PRODUTOS ==========

@app.route('/products')
def products_page():
    """Página principal de produtos"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Buscar produtos do banco de dados
    products = get_all_products()
    categories = get_categories()
    
    return render_template('Products/products.html', 
                         products=products, 
                         categories=categories,
                         selected_category=None)

@app.route('/products/search')
def search_products():
    """Buscar produtos por termo e categoria"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    search_term = request.args.get('q', '')
    category = request.args.get('category', '')
    
    products = search_products_db(search_term, category if category != 'all' else None)
    categories = get_categories()
    
    return render_template('Products/products.html', 
                         products=products, 
                         categories=categories,
                         search_term=search_term,
                         selected_category=category)

@app.route('/products/<int:product_id>')
def product_detail(product_id):
    """Página de detalhes do produto"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    product = get_product_by_id(product_id)
    
    if product is None:
        flash('Produto não encontrado!', 'error')
        return redirect(url_for('products_page'))
    
    return render_template('Products/product_detail.html', product=product)

@app.route('/products/new', methods=['GET', 'POST'])
def new_product():
    """Página para cadastrar novo produto"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    categories = get_categories()
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category = request.form.get('category', '').strip()
        units_per_box = request.form.get('units_per_box', '').strip()
        price = request.form.get('price', '').strip()
        description = request.form.get('description', '').strip()
        image = request.form.get('image', '').strip()
        
        # Validações
        if not name or not category or not units_per_box:
            flash('Por favor, preencha todos os campos obrigatórios!', 'error')
            return render_template('Products/product_form.html', 
                                 categories=categories, 
                                 product=None)
        
        try:
            units_per_box = int(units_per_box)
            if units_per_box <= 0:
                flash('Unidades por caixa deve ser maior que zero!', 'error')
                return render_template('Products/product_form.html', 
                                     categories=categories, 
                                     product=None)
        except ValueError:
            flash('Unidades por caixa deve ser um número válido!', 'error')
            return render_template('Products/product_form.html', 
                                 categories=categories, 
                                 product=None)
        
        # Processar preço
        price_value = None
        if price:
            try:
                price_value = float(price)
                if price_value < 0:
                    flash('Preço não pode ser negativo!', 'error')
                    return render_template('Products/product_form.html', 
                                         categories=categories, 
                                         product=None)
            except ValueError:
                flash('Preço deve ser um valor numérico válido!', 'error')
                return render_template('Products/product_form.html', 
                                     categories=categories, 
                                     product=None)
        
        # Criar produto
        product_id = create_product(name, category, units_per_box, price_value, description, image)
        
        if product_id:
            flash('Produto cadastrado com sucesso!', 'success')
            return redirect(url_for('product_detail', product_id=product_id))
        else:
            flash('Erro ao cadastrar produto!', 'error')
    
    return render_template('Products/product_form.html', 
                         categories=categories, 
                         product=None)

@app.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
def edit_product(product_id):
    """Página para editar produto existente"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    product = get_product_by_id(product_id)
    categories = get_categories()
    
    if product is None:
        flash('Produto não encontrado!', 'error')
        return redirect(url_for('products_page'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category = request.form.get('category', '').strip()
        units_per_box = request.form.get('units_per_box', '').strip()
        price = request.form.get('price', '').strip()
        description = request.form.get('description', '').strip()
        image = request.form.get('image', '').strip()
        
        # Validações
        if not name or not category or not units_per_box:
            flash('Por favor, preencha todos os campos obrigatórios!', 'error')
            return render_template('Products/product_form.html', 
                                 categories=categories, 
                                 product=product)
        
        try:
            units_per_box = int(units_per_box)
            if units_per_box <= 0:
                flash('Unidades por caixa deve ser maior que zero!', 'error')
                return render_template('Products/product_form.html', 
                                     categories=categories, 
                                     product=product)
        except ValueError:
            flash('Unidades por caixa deve ser um número válido!', 'error')
            return render_template('Products/product_form.html', 
                                 categories=categories, 
                                 product=product)
        
        # Processar preço
        price_value = None
        if price:
            try:
                price_value = float(price)
                if price_value < 0:
                    flash('Preço não pode ser negativo!', 'error')
                    return render_template('Products/product_form.html', 
                                         categories=categories, 
                                         product=product)
            except ValueError:
                flash('Preço deve ser um valor numérico válido!', 'error')
                return render_template('Products/product_form.html', 
                                     categories=categories, 
                                     product=product)
        
        # Atualizar produto
        if update_product(product_id, name, category, units_per_box, price_value, description, image):
            flash('Produto atualizado com sucesso!', 'success')
            return redirect(url_for('product_detail', product_id=product_id))
        else:
            flash('Erro ao atualizar produto!', 'error')
    
    return render_template('Products/product_form.html', 
                         categories=categories, 
                         product=product)

@app.route('/products/<int:product_id>/delete', methods=['POST'])
def delete_product_route(product_id):
    """Rota para excluir produto"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if delete_product(product_id):
        flash('Produto excluído com sucesso!', 'success')
    else:
        flash('Erro ao excluir produto!', 'error')
    
    return redirect(url_for('products_page'))

@app.route('/api/products')
def api_products():
    """Endpoint da API para retornar produtos em JSON"""
    if 'username' not in session:
        return jsonify({'error': 'Não autorizado'}), 401
    
    products = get_all_products()
    # Converter Row objects para dicionários
    products_list = [dict(product) for product in products]
    return jsonify(products_list)

if __name__ == '__main__':
    # Inicializar o banco de dados na primeira execução
    init_db()
    app.run(debug=True)
