-- ============================================================
-- HR Analytics Platform — MySQL Database Schema
-- INX Future Inc. Employee Performance Prediction System
-- ============================================================

CREATE DATABASE IF NOT EXISTS hr_analytics
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE hr_analytics;

-- ─────────────────────────────────────────────────────────────
-- TABLE 1: Departments
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Departments (
    DepartmentID    INT             NOT NULL AUTO_INCREMENT,
    DepartmentName  VARCHAR(100)    NOT NULL,
    DepartmentHead  VARCHAR(100)    NOT NULL,
    Budget          DECIMAL(15,2)   NOT NULL DEFAULT 0.00,
    Location        VARCHAR(100)    NOT NULL,
    CreatedAt       TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (DepartmentID),
    UNIQUE KEY uq_dept_name (DepartmentName)
) ENGINE=InnoDB;

-- Seed department data
INSERT INTO Departments (DepartmentName, DepartmentHead, Budget, Location) VALUES
('Sales',                   'Michael Thompson',   15000000.00, 'New York'),
('Research & Development',  'Dr. Priya Sharma',   25000000.00, 'San Francisco'),
('Human Resources',         'Amanda Collins',      5000000.00, 'Chicago'),
('Finance',                 'Robert Martinez',     8000000.00, 'Dallas'),
('Operations',              'Linda Wong',         12000000.00, 'Seattle');

-- ─────────────────────────────────────────────────────────────
-- TABLE 2: Employees
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Employees (
    EmployeeID              INT             NOT NULL,
    EmployeeName            VARCHAR(150)    NOT NULL,
    Age                     TINYINT         NOT NULL,
    Gender                  ENUM('Male','Female','Other') NOT NULL,
    MaritalStatus           ENUM('Single','Married','Divorced') NOT NULL,
    Education               TINYINT         NOT NULL COMMENT '1=Below College, 2=College, 3=Bachelor, 4=Master, 5=Doctor',
    EducationField          VARCHAR(100)    NOT NULL,
    DepartmentID            INT             NOT NULL,
    JobRole                 VARCHAR(100)    NOT NULL,
    JobLevel                TINYINT         NOT NULL,
    BusinessTravel          VARCHAR(50)     NOT NULL,
    MonthlyIncome           INT             NOT NULL,
    PercentSalaryHike       TINYINT         NOT NULL,
    StockOptionLevel        TINYINT         NOT NULL,
    TotalWorkingYears       INT             NOT NULL DEFAULT 0,
    TrainingTimesLastYear   TINYINT         NOT NULL DEFAULT 0,
    YearsAtCompany          INT             NOT NULL DEFAULT 0,
    YearsInCurrentRole      INT             NOT NULL DEFAULT 0,
    YearsSinceLastPromotion INT             NOT NULL DEFAULT 0,
    YearsWithCurrManager    INT             NOT NULL DEFAULT 0,
    NumCompaniesWorked      INT             NOT NULL DEFAULT 0,
    DistanceFromHome        INT             NOT NULL DEFAULT 0,
    Attrition               ENUM('Yes','No') NOT NULL DEFAULT 'No',
    PerformanceRating       TINYINT         NOT NULL COMMENT '3=Medium, 4=High',
    PerformanceLabel        ENUM('Low','Medium','High') NOT NULL DEFAULT 'Medium',
    CreatedAt               TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt               TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (EmployeeID),
    KEY idx_dept       (DepartmentID),
    KEY idx_perf       (PerformanceRating),
    KEY idx_attrition  (Attrition),
    KEY idx_jobrole    (JobRole),
    CONSTRAINT fk_emp_dept FOREIGN KEY (DepartmentID)
        REFERENCES Departments(DepartmentID) ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ─────────────────────────────────────────────────────────────
-- TABLE 3: EmployeeSurvey
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS EmployeeSurvey (
    SurveyID                INT             NOT NULL AUTO_INCREMENT,
    EmployeeID              INT             NOT NULL,
    EnvironmentSatisfaction TINYINT         NOT NULL COMMENT '1=Low,2=Medium,3=High,4=Very High',
    JobSatisfaction         TINYINT         NOT NULL COMMENT '1=Low,2=Medium,3=High,4=Very High',
    WorkLifeBalance         TINYINT         NOT NULL COMMENT '1=Bad,2=Good,3=Better,4=Best',
    SurveyDate              DATE            DEFAULT (CURRENT_DATE),
    PRIMARY KEY (SurveyID),
    KEY idx_survey_emp (EmployeeID),
    CONSTRAINT fk_survey_emp FOREIGN KEY (EmployeeID)
        REFERENCES Employees(EmployeeID) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ─────────────────────────────────────────────────────────────
-- TABLE 4: ManagerSurvey
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ManagerSurvey (
    ManagerSurveyID     INT         NOT NULL AUTO_INCREMENT,
    EmployeeID          INT         NOT NULL,
    JobInvolvement      TINYINT     NOT NULL COMMENT '1=Low,2=Medium,3=High,4=Very High',
    ManagerRating       TINYINT     NOT NULL COMMENT '1=Low to 5=Excellent (derived)',
    LeadershipScore     DECIMAL(4,2) NOT NULL DEFAULT 0.00,
    CommunicationScore  DECIMAL(4,2) NOT NULL DEFAULT 0.00,
    PRIMARY KEY (ManagerSurveyID),
    KEY idx_mgr_emp (EmployeeID),
    CONSTRAINT fk_mgr_emp FOREIGN KEY (EmployeeID)
        REFERENCES Employees(EmployeeID) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ─────────────────────────────────────────────────────────────
-- TABLE 5: Attendance
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Attendance (
    AttendanceID    BIGINT          NOT NULL AUTO_INCREMENT,
    EmployeeID      INT             NOT NULL,
    AttendanceDate  DATE            NOT NULL,
    LoginTime       DATETIME        NULL,
    LogoutTime      DATETIME        NULL,
    WorkingHours    DECIMAL(5,2)    NOT NULL DEFAULT 0.00,
    OvertimeHours   DECIMAL(5,2)    NOT NULL DEFAULT 0.00,
    IsAbsent        TINYINT(1)      NOT NULL DEFAULT 0,
    IsLate          TINYINT(1)      NOT NULL DEFAULT 0,
    PRIMARY KEY (AttendanceID),
    UNIQUE KEY uq_emp_date (EmployeeID, AttendanceDate),
    KEY idx_att_emp  (EmployeeID),
    KEY idx_att_date (AttendanceDate),
    CONSTRAINT fk_att_emp FOREIGN KEY (EmployeeID)
        REFERENCES Employees(EmployeeID) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ─────────────────────────────────────────────────────────────
-- TABLE 6: Projects
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Projects (
    ProjectID       INT             NOT NULL AUTO_INCREMENT,
    ProjectName     VARCHAR(200)    NOT NULL,
    ProjectType     ENUM('Internal','External','Research','Development','Support') NOT NULL,
    Budget          DECIMAL(15,2)   NOT NULL DEFAULT 0.00,
    StartDate       DATE            NOT NULL,
    EndDate         DATE            NULL,
    Status          ENUM('Active','Completed','On Hold','Cancelled') NOT NULL DEFAULT 'Active',
    PRIMARY KEY (ProjectID)
) ENGINE=InnoDB;

-- ─────────────────────────────────────────────────────────────
-- TABLE 7: EmployeeProjects
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS EmployeeProjects (
    ID                  INT     NOT NULL AUTO_INCREMENT,
    EmployeeID          INT     NOT NULL,
    ProjectID           INT     NOT NULL,
    RoleInProject       VARCHAR(100) NOT NULL,
    HoursWorked         DECIMAL(8,2) NOT NULL DEFAULT 0.00,
    CompletionStatus    ENUM('Not Started','In Progress','Completed','Delayed') NOT NULL DEFAULT 'In Progress',
    ProjectScore        DECIMAL(4,2) NOT NULL DEFAULT 0.00 COMMENT 'Score out of 10',
    PRIMARY KEY (ID),
    UNIQUE KEY uq_emp_proj (EmployeeID, ProjectID),
    KEY idx_ep_emp  (EmployeeID),
    KEY idx_ep_proj (ProjectID),
    CONSTRAINT fk_ep_emp  FOREIGN KEY (EmployeeID) REFERENCES Employees(EmployeeID) ON DELETE CASCADE,
    CONSTRAINT fk_ep_proj FOREIGN KEY (ProjectID)  REFERENCES Projects(ProjectID)   ON DELETE CASCADE
) ENGINE=InnoDB;

-- ─────────────────────────────────────────────────────────────
-- TABLE 8: TrainingPrograms
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS TrainingPrograms (
    TrainingID      INT             NOT NULL AUTO_INCREMENT,
    TrainingName    VARCHAR(200)    NOT NULL,
    Category        ENUM('Technical','Leadership','Communication','Compliance','Safety','Sales','Management') NOT NULL,
    DurationHours   DECIMAL(6,2)    NOT NULL,
    Description     TEXT            NULL,
    PRIMARY KEY (TrainingID)
) ENGINE=InnoDB;

-- Seed training programs
INSERT INTO TrainingPrograms (TrainingName, Category, DurationHours, Description) VALUES
('Advanced Python for Data Science',    'Technical',      40.0, 'Python, Pandas, ML libraries'),
('Leadership Excellence Program',       'Leadership',     24.0, 'Strategic thinking and leadership skills'),
('Effective Business Communication',    'Communication',  16.0, 'Presentation and writing skills'),
('Workplace Safety & Compliance',       'Compliance',      8.0, 'Safety regulations and compliance'),
('Sales Mastery Bootcamp',              'Sales',          32.0, 'Advanced sales techniques'),
('Project Management Professional',     'Management',     40.0, 'PMP methodology and tools'),
('Cloud Computing Fundamentals',        'Technical',      24.0, 'AWS, Azure, GCP basics'),
('HR Analytics & Workforce Planning',   'Technical',      20.0, 'Data-driven HR decisions'),
('Negotiation & Conflict Resolution',   'Communication',  12.0, 'Win-win negotiation strategies'),
('Financial Analysis for Managers',     'Management',     16.0, 'Budget and financial decision making');

-- ─────────────────────────────────────────────────────────────
-- TABLE 9: EmployeeTraining
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS EmployeeTraining (
    ID                  INT         NOT NULL AUTO_INCREMENT,
    EmployeeID          INT         NOT NULL,
    TrainingID          INT         NOT NULL,
    EnrollDate          DATE        NOT NULL,
    CompletionDate      DATE        NULL,
    CompletionStatus    ENUM('Enrolled','In Progress','Completed','Failed','Dropped') NOT NULL DEFAULT 'Enrolled',
    AssessmentScore     DECIMAL(5,2) NOT NULL DEFAULT 0.00 COMMENT 'Score out of 100',
    PRIMARY KEY (ID),
    KEY idx_et_emp  (EmployeeID),
    KEY idx_et_trn  (TrainingID),
    CONSTRAINT fk_et_emp FOREIGN KEY (EmployeeID) REFERENCES Employees(EmployeeID) ON DELETE CASCADE,
    CONSTRAINT fk_et_trn FOREIGN KEY (TrainingID) REFERENCES TrainingPrograms(TrainingID) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ─────────────────────────────────────────────────────────────
-- TABLE 10: Promotions
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS Promotions (
    PromotionID     INT             NOT NULL AUTO_INCREMENT,
    EmployeeID      INT             NOT NULL,
    PromotionDate   DATE            NOT NULL,
    PreviousRole    VARCHAR(100)    NOT NULL,
    NewRole         VARCHAR(100)    NOT NULL,
    SalaryBefore    INT             NOT NULL DEFAULT 0,
    SalaryAfter     INT             NOT NULL DEFAULT 0,
    Remarks         TEXT            NULL,
    PRIMARY KEY (PromotionID),
    KEY idx_promo_emp (EmployeeID),
    CONSTRAINT fk_promo_emp FOREIGN KEY (EmployeeID)
        REFERENCES Employees(EmployeeID) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;

-- ─────────────────────────────────────────────────────────────
-- ANALYTICAL VIEWS
-- ─────────────────────────────────────────────────────────────

-- View 1: Employee Full Profile
CREATE OR REPLACE VIEW vw_EmployeeFullProfile AS
SELECT
    e.EmployeeID,
    e.EmployeeName,
    e.Age,
    e.Gender,
    e.MaritalStatus,
    e.Education,
    e.EducationField,
    d.DepartmentName,
    d.Location,
    e.JobRole,
    e.JobLevel,
    e.BusinessTravel,
    e.MonthlyIncome,
    e.PercentSalaryHike,
    e.StockOptionLevel,
    e.TotalWorkingYears,
    e.YearsAtCompany,
    e.YearsInCurrentRole,
    e.YearsSinceLastPromotion,
    e.TrainingTimesLastYear,
    e.Attrition,
    e.PerformanceRating,
    e.PerformanceLabel,
    es.EnvironmentSatisfaction,
    es.JobSatisfaction,
    es.WorkLifeBalance,
    ms.JobInvolvement,
    ms.ManagerRating,
    ms.LeadershipScore,
    ms.CommunicationScore
FROM Employees e
JOIN Departments   d  ON e.DepartmentID  = d.DepartmentID
LEFT JOIN EmployeeSurvey es ON e.EmployeeID = es.EmployeeID
LEFT JOIN ManagerSurvey  ms ON e.EmployeeID = ms.EmployeeID;

-- View 2: Department KPI Summary
CREATE OR REPLACE VIEW vw_DepartmentKPIs AS
SELECT
    d.DepartmentID,
    d.DepartmentName,
    d.DepartmentHead,
    d.Budget,
    d.Location,
    COUNT(e.EmployeeID)                         AS TotalEmployees,
    ROUND(AVG(e.MonthlyIncome),2)               AS AvgSalary,
    ROUND(AVG(e.PerformanceRating),2)           AS AvgPerformance,
    SUM(CASE WHEN e.Attrition='Yes' THEN 1 ELSE 0 END) AS AttritionCount,
    ROUND(100.0 * SUM(CASE WHEN e.Attrition='Yes' THEN 1 ELSE 0 END) / COUNT(*), 2) AS AttritionRate,
    ROUND(AVG(es.JobSatisfaction),2)            AS AvgJobSatisfaction,
    ROUND(AVG(es.WorkLifeBalance),2)            AS AvgWorkLifeBalance,
    ROUND(AVG(ms.JobInvolvement),2)             AS AvgJobInvolvement,
    SUM(CASE WHEN e.PerformanceLabel='High' THEN 1 ELSE 0 END)   AS HighPerformers,
    SUM(CASE WHEN e.PerformanceLabel='Medium' THEN 1 ELSE 0 END) AS MediumPerformers,
    SUM(CASE WHEN e.PerformanceLabel='Low' THEN 1 ELSE 0 END)    AS LowPerformers
FROM Departments d
LEFT JOIN Employees     e  ON d.DepartmentID = e.DepartmentID
LEFT JOIN EmployeeSurvey es ON e.EmployeeID  = es.EmployeeID
LEFT JOIN ManagerSurvey  ms ON e.EmployeeID  = ms.EmployeeID
GROUP BY d.DepartmentID, d.DepartmentName, d.DepartmentHead, d.Budget, d.Location;

-- View 3: Attendance Summary per Employee
CREATE OR REPLACE VIEW vw_AttendanceSummary AS
SELECT
    e.EmployeeID,
    e.EmployeeName,
    d.DepartmentName,
    COUNT(a.AttendanceDate)                         AS WorkingDays,
    SUM(a.IsAbsent)                                 AS AbsentDays,
    SUM(a.IsLate)                                   AS LateDays,
    ROUND(AVG(a.WorkingHours),2)                    AS AvgWorkingHours,
    ROUND(SUM(a.OvertimeHours),2)                   AS TotalOvertimeHours,
    ROUND(100.0*(COUNT(a.AttendanceDate)-SUM(a.IsAbsent))/NULLIF(COUNT(a.AttendanceDate),0),2) AS AttendanceRate
FROM Employees e
JOIN Departments d ON e.DepartmentID = d.DepartmentID
LEFT JOIN Attendance a ON e.EmployeeID = a.EmployeeID
GROUP BY e.EmployeeID, e.EmployeeName, d.DepartmentName;

-- View 4: Training Effectiveness
CREATE OR REPLACE VIEW vw_TrainingEffectiveness AS
SELECT
    tp.TrainingID,
    tp.TrainingName,
    tp.Category,
    tp.DurationHours,
    COUNT(et.EmployeeID)                                    AS TotalEnrolled,
    SUM(CASE WHEN et.CompletionStatus='Completed' THEN 1 ELSE 0 END) AS Completed,
    ROUND(100.0*SUM(CASE WHEN et.CompletionStatus='Completed' THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0),2) AS CompletionRate,
    ROUND(AVG(CASE WHEN et.CompletionStatus='Completed' THEN et.AssessmentScore END),2) AS AvgScore,
    ROUND(AVG(CASE WHEN et.CompletionStatus='Completed' THEN e.PerformanceRating END),2) AS AvgPerformanceAfter
FROM TrainingPrograms tp
LEFT JOIN EmployeeTraining et ON tp.TrainingID = et.TrainingID
LEFT JOIN Employees e         ON et.EmployeeID = e.EmployeeID
GROUP BY tp.TrainingID, tp.TrainingName, tp.Category, tp.DurationHours;

-- View 5: Promotion Readiness Score
CREATE OR REPLACE VIEW vw_PromotionReadiness AS
SELECT
    e.EmployeeID,
    e.EmployeeName,
    d.DepartmentName,
    e.JobRole,
    e.JobLevel,
    e.PerformanceLabel,
    e.YearsAtCompany,
    e.YearsSinceLastPromotion,
    e.TotalWorkingYears,
    es.JobSatisfaction,
    ms.JobInvolvement,
    ms.ManagerRating,
    ROUND(
        (e.PerformanceRating * 20)
        + (ms.JobInvolvement * 10)
        + (es.JobSatisfaction * 5)
        + (CASE WHEN e.YearsSinceLastPromotion >= 3 THEN 20 ELSE e.YearsSinceLastPromotion * 5 END)
        + (CASE WHEN e.Attrition = 'No' THEN 10 ELSE 0 END)
    , 2) AS PromotionReadinessScore
FROM Employees e
JOIN Departments    d  ON e.DepartmentID = d.DepartmentID
LEFT JOIN EmployeeSurvey es ON e.EmployeeID = es.EmployeeID
LEFT JOIN ManagerSurvey  ms ON e.EmployeeID = ms.EmployeeID;
