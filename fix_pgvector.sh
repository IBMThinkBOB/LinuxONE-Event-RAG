#!/bin/bash

# Fix pgvector installation for PostgreSQL@15

set -e

echo "=========================================="
echo "Fixing pgvector installation"
echo "=========================================="
echo ""

# Find pgvector installation
PGVECTOR_PATH=$(brew --prefix pgvector)
PG_EXTENSION_DIR="/opt/homebrew/opt/postgresql@15/share/postgresql@15/extension"
PG_LIB_DIR="/opt/homebrew/opt/postgresql@15/lib/postgresql"

echo "pgvector path: $PGVECTOR_PATH"
echo "PostgreSQL extension dir: $PG_EXTENSION_DIR"
echo "PostgreSQL lib dir: $PG_LIB_DIR"
echo ""

# Create symlinks
echo "Creating symlinks..."

# Link control file
if [ -f "$PGVECTOR_PATH/share/postgresql@15/extension/vector.control" ]; then
    ln -sf "$PGVECTOR_PATH/share/postgresql@15/extension/vector.control" "$PG_EXTENSION_DIR/vector.control"
    echo "✓ Linked vector.control"
fi

# Link SQL files
for sql_file in "$PGVECTOR_PATH/share/postgresql@15/extension"/vector--*.sql; do
    if [ -f "$sql_file" ]; then
        filename=$(basename "$sql_file")
        ln -sf "$sql_file" "$PG_EXTENSION_DIR/$filename"
        echo "✓ Linked $filename"
    fi
done

# Link library file
if [ -f "$PGVECTOR_PATH/lib/postgresql/vector.so" ]; then
    ln -sf "$PGVECTOR_PATH/lib/postgresql/vector.so" "$PG_LIB_DIR/vector.so"
    echo "✓ Linked vector.so"
fi

echo ""
echo "Restarting PostgreSQL..."
brew services restart postgresql@15
sleep 3

echo ""
echo "Testing pgvector installation..."
psql -U raguser -d linuxone_rag -c "CREATE EXTENSION IF NOT EXISTS vector;" && echo "✓ pgvector extension created successfully!" || echo "✗ Failed to create extension"

echo ""
echo "Running database initialization..."
psql -U raguser -d linuxone_rag -f backend/scripts/init_db.sql && echo "✓ Database initialized!" || echo "✗ Initialization had errors (may be okay if tables already exist)"

echo ""
echo "=========================================="
echo "pgvector setup complete!"
echo "=========================================="
echo ""
echo "Verify with:"
echo "  psql -U raguser -d linuxone_rag -c \"SELECT * FROM pg_extension WHERE extname = 'vector';\""
echo ""

# Made with Bob
