-- ==============================================================================
-- Schema: enterprise_oltp
-- Description: Highly normalized 3NF schema for OLTP operations
-- ==============================================================================

CREATE DATABASE IF NOT EXISTS enterprise_oltp;
USE enterprise_oltp;

-- 1. Departments Table
CREATE TABLE IF NOT EXISTS departments (
    department_id INT AUTO_INCREMENT PRIMARY KEY,
    department_name VARCHAR(100) NOT NULL UNIQUE,
    cost_center_code VARCHAR(50) NOT NULL,
    location VARCHAR(100) NOT NULL DEFAULT 'Headquarters',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 2. Employees Table (Current state in OLTP)
CREATE TABLE IF NOT EXISTS employees (
    employee_id INT AUTO_INCREMENT PRIMARY KEY,
    employee_number VARCHAR(20) NOT NULL UNIQUE,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    gender VARCHAR(20),
    age INT,
    department_id INT NOT NULL,
    job_role VARCHAR(100) NOT NULL,
    job_level INT NOT NULL DEFAULT 1,
    monthly_income DECIMAL(12, 2) NOT NULL,
    education_field VARCHAR(100),
    years_at_company INT DEFAULT 0,
    attrition ENUM('Yes', 'No') DEFAULT 'No',
    hire_date DATE NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_emp_dept FOREIGN KEY (department_id) REFERENCES departments (department_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- 3. Projects Table
CREATE TABLE IF NOT EXISTS projects (
    project_id INT AUTO_INCREMENT PRIMARY KEY,
    project_code VARCHAR(20) NOT NULL UNIQUE,
    project_name VARCHAR(150) NOT NULL,
    department_id INT NOT NULL,
    priority ENUM('Low', 'Medium', 'High', 'Critical') DEFAULT 'Medium',
    status ENUM('Planning', 'Active', 'On Hold', 'Completed', 'Cancelled') DEFAULT 'Active',
    start_date DATE NOT NULL,
    end_date DATE NULL,
    budget DECIMAL(15, 2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_proj_dept FOREIGN KEY (department_id) REFERENCES departments (department_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- 4. Project Assignments Table
CREATE TABLE IF NOT EXISTS project_assignments (
    assignment_id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT NOT NULL,
    project_id INT NOT NULL,
    assigned_role VARCHAR(100) NOT NULL,
    allocation_pct INT NOT NULL CHECK (allocation_pct BETWEEN 1 AND 100),
    assigned_date DATE NOT NULL,
    released_date DATE NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_asgn_emp FOREIGN KEY (employee_id) REFERENCES employees (employee_id) ON DELETE CASCADE,
    CONSTRAINT fk_asgn_proj FOREIGN KEY (project_id) REFERENCES projects (project_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 5. Performance Reviews Table
CREATE TABLE IF NOT EXISTS performance_reviews (
    review_id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT NOT NULL,
    review_date DATE NOT NULL,
    review_cycle VARCHAR(20) NOT NULL, -- e.g. '2024-Q4' or 'Annual-2024'
    performance_rating INT NOT NULL CHECK (performance_rating BETWEEN 1 AND 5),
    work_life_balance INT NOT NULL CHECK (work_life_balance BETWEEN 1 AND 4),
    job_satisfaction INT NOT NULL CHECK (job_satisfaction BETWEEN 1 AND 4),
    training_times_last_year INT DEFAULT 0,
    reviewer_comments TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_rev_emp FOREIGN KEY (employee_id) REFERENCES employees (employee_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Indexes for OLTP query optimization
CREATE INDEX idx_emp_dept ON employees(department_id);
CREATE INDEX idx_emp_hire ON employees(hire_date);
CREATE INDEX idx_proj_status ON projects(status);
CREATE INDEX idx_rev_emp_date ON performance_reviews(employee_id, review_date);
