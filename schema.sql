DROP TABLE IF EXISTS User;

CREATE TABLE User (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    Name TEXT NOT NULL,
    Email TEXT UNIQUE NOT NULL,
    Password TEXT NOT NULL,
    UserType TEXT CHECK(UserType IN ('Attendee', 'Organizer')) NOT NULL,
    Interests TEXT
);

CREATE TABLE IF NOT EXISTS Venue (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    Name TEXT NOT NULL,
    Address TEXT,
    Capacity INTEGER
);


DROP TABLE IF EXISTS Event;

CREATE TABLE Event (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    Name TEXT NOT NULL,
    Venue TEXT NOT NULL,
    DateTime TEXT NOT NULL,
    TicketPrice REAL NOT NULL,
    AvailableTickets INTEGER NOT NULL 
);


CREATE TABLE IF NOT EXISTS Ticket (
    TicketID INTEGER PRIMARY KEY AUTOINCREMENT,
    EventID INTEGER,
    UserID INTEGER,
    PurchaseDate TEXT,
    Quantity INTEGER NOT NULL,
    FOREIGN KEY (EventID) REFERENCES Event(EventID),
    FOREIGN KEY (UserID) REFERENCES User(UserID)
);

CREATE TABLE IF NOT EXISTS Message (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    SenderId INTEGER NOT NULL,
    ReceiverId INTEGER NOT NULL,
    Content TEXT NOT NULL,
    FOREIGN KEY (SenderId) REFERENCES User(Id),
    FOREIGN KEY (ReceiverId) REFERENCES User(Id)
);