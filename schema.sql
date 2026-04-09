-- Схема для MS Access (таблицы "Subscribers" и "Phones")
-- Тестировалась в логике: телефоны принадлежат абоненту (1:N).
--
-- Перед запуском убедитесь, что таблицы еще не существуют.

CREATE TABLE Subscribers (
    Id COUNTER,
    FullName TEXT(200),
    PassportId TEXT(50),
    Address TEXT(255)
);

CREATE TABLE Phones (
    Id COUNTER,
    Number TEXT(30),
    Operator TEXT(100),
    Status INTEGER,
    SubscriberId LONG
);

-- Уникальность номера.
ALTER TABLE Phones
ADD CONSTRAINT UQ_Phones_Number UNIQUE (Number);

-- Внешний ключ (может не сработать в некоторых версиях/настройках Access).
-- Если не создастся — приложение всё равно работает, целостность поддерживается в коде.
ALTER TABLE Phones
ADD CONSTRAINT FK_Phones_Subscribers FOREIGN KEY (SubscriberId) REFERENCES Subscribers(Id);

