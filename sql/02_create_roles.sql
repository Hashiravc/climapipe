-- ==============================================================================
-- ClimaData Perú: Separación de Roles (Principio de Menor Privilegio)
-- ==============================================================================

-- 1. Rol de Escritura (Utilizado por el Pipeline ELT y dbt)
-- En Neon, el usuario por defecto (neondb_owner) tiene permisos de DDL y DML.
-- Para entornos dedicados se puede crear un rol específico:
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'elt_writer') THEN
        CREATE ROLE elt_writer WITH LOGIN PASSWORD 'CAMBIAR_PASSWORD_ESCRITURA';
    END IF;
END
$$;

GRANT USAGE, CREATE ON SCHEMA raw TO elt_writer;
GRANT USAGE, CREATE ON SCHEMA marts TO elt_writer;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA raw TO elt_writer;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA marts TO elt_writer;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT ALL ON TABLES TO elt_writer;
ALTER DEFAULT PRIVILEGES IN SCHEMA marts GRANT ALL ON TABLES TO elt_writer;

-- 2. Rol de Solo Lectura (Utilizado por el Dashboard de Streamlit)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'streamlit_reader') THEN
        CREATE ROLE streamlit_reader WITH LOGIN PASSWORD 'CAMBIAR_PASSWORD_LECTURA';
    END IF;
END
$$;

-- Otorgar únicamente lectura (SELECT) en raw y marts
GRANT USAGE ON SCHEMA raw TO streamlit_reader;
GRANT USAGE ON SCHEMA marts TO streamlit_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA raw TO streamlit_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA marts TO streamlit_reader;

-- Asegurar que futuras tablas creadas por dbt en marts sean automáticamente legibles por streamlit_reader
ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT SELECT ON TABLES TO streamlit_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA marts GRANT SELECT ON TABLES TO streamlit_reader;
