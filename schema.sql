-- ArtesaníasPlus - esquema de base de datos (MySQL 8 / MariaDB 10.5+)
CREATE DATABASE IF NOT EXISTS artesanias_plus
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE artesanias_plus;

CREATE TABLE IF NOT EXISTS pedidos (
  id            VARCHAR(40)   NOT NULL PRIMARY KEY,
  cliente       VARCHAR(120)  NOT NULL,
  producto      VARCHAR(120)  NOT NULL,
  monto         DECIMAL(10,2) NOT NULL,
  estado_pago   ENUM('Pagado','Pendiente') NOT NULL,
  estado_envio  ENUM('Pendiente','Enviado','Entregado') NOT NULL,
  guia          VARCHAR(60)   NOT NULL DEFAULT '',
  notas         VARCHAR(255)  NOT NULL DEFAULT '',
  fecha         DATE          NULL,
  actualizado   DATETIME      NOT NULL
);

-- El historial solo recibe inserciones: nunca se modifica ni se borra.
CREATE TABLE IF NOT EXISTS historial (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  pedido_id   VARCHAR(40)  NOT NULL,
  fecha       DATETIME     NOT NULL,
  tipo        ENUM('Alta','Cambio') NOT NULL,
  detalle     TEXT         NOT NULL,
  origen      VARCHAR(20)  NOT NULL,
  INDEX idx_historial_pedido (pedido_id),
  INDEX idx_historial_fecha (fecha)
);
