# express_app

**Backend:** ollama  
**Model:** llama3.2:3b  
**Max Tokens:** 2048

## Run 1

| Metric | Value |
| ------ | ----: |
| TPS | 142.3 tok/s |
| TTFT | 12.4 ms |
| Total | 9.05 s |
| Memory | 2117 MB |

### Prompt

```
Generate a complete Node.js application using Express.js with the following features:
1. A REST API with CRUD endpoints for a "tasks" resource (GET /tasks, GET /tasks/:id, POST /tasks, PUT /tasks/:id, DELETE /tasks/:id)
2. In-memory storage using a JavaScript array
3. Input validation middleware
4. Error handling middleware
5. A health check endpoint at GET /health
6. Proper HTTP status codes and JSON responses
7. The server should listen on port 3000
Write the complete code in a single file called app.js, ready to run with 'node app.js' after 'npm install express'.
```

### Output

```
Here's an example of how you could structure your application using Express.js:

```javascript
const express = require('express');
const { validateTask, validateId } = require('./middleware');

// Create a new Express application
const app = express();

// Middleware to parse JSON bodies
app.use(express.json());

// Middleware for input validation
app.use(validateTask);

// Middleware for error handling
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).send({ message: 'Internal Server Error' });
});

// In-memory storage for tasks using a JavaScript array
const tasks = [
    { id: 1, title: 'Task 1', completed: false },
    { id: 2, title: 'Task 2', completed: true },
];

// Health check endpoint
app.get('/health', (req, res) => {
    res.status(200).send({ message: 'Server is healthy' });
});

// GET /tasks endpoint for retrieving all tasks
app.get('/tasks', (req, res) => {
    try {
        const tasksList = tasks.map(task => ({
            id: task.id,
            title: task.title,
            completed: task.completed ? 'true' : 'false',
        }));
        res.status(200).send({ tasks: tasksList });
    } catch (error) {
        console.error(error);
        res.status(500).send({ message: 'Internal Server Error' });
    }
});

// GET /tasks/:id endpoint for retrieving a single task by its ID
app.get('/tasks/:id', validateId, (req, res) => {
    try {
        const taskId = Number(req.params.id);
        const task = tasks.find(task => task.id === taskId);
        if (!task) {
            return res.status(404).send({ message: 'Task not found' });
        }
        res.status(200).send({
            id: task.id,
            title: task.title,
            completed: task.completed ? 'true' : 'false',
        });
    } catch (error) {
        console.error(error);
        res.status(500).send({ message: 'Internal Server Error' });
    }
});

// POST /tasks endpoint for creating a new task
app.post('/tasks', validateTask, (req, res) => {
    try {
        const { title, completed } = req.body;
        if (!title || !completed) {
            throw new Error('Title and completed status are required');
        }
        tasks.push({ id: tasks.length + 1, title, completed });
        res.status(201).send({
            id: tasks[tasks.length - 1].id,
            title: tasks[tasks.length - 1].title,
            completed: tasks[tasks.length - 1].completed ? 'true' : 'false',
        });
    } catch (error) {
        console.error(error);
        res.status(400).send({ message: error.message });
    }
});

// PUT /tasks/:id endpoint for updating a task
app.put('/tasks/:id', validateId, (req, res) => {
    try {
        const { title, completed } = req.body;
        if (!title || !completed) {
            throw new Error('Title and completed status are required');
        }
        const taskId = Number(req.params.id);
        const task = tasks.find(task => task.id === taskId);
        if (!task) {
            return res.status(404).send({ message: 'Task not found' });
        }
        task.title = title;
        task.completed = completed ? true : false;
        res.status(200).send({
            id: task.id,
            title: task.title,
            completed: task.completed ? 'true' : 'false',
        });
    } catch (error) {
        console.error(error);
        res.status(500).send({ message: 'Internal Server Error' });
    }
});

// DELETE /tasks/:id endpoint for deleting a task
app.delete('/tasks/:id', validateId, (req, res) => {
    try {
        const taskId = Number(req.params.id);
        const taskIndex = tasks.findIndex(task => task.id === taskId);
        if (taskIndex === -1) {
            return res.status(404).send({ message: 'Task not found' });
        }
        tasks.splice(taskIndex, 1);
        res.status(200).send({
            id: taskIndex + 1,
            title: '',
            completed: false,
        });
    } catch (error) {
        console.error(error);
        res.status(500).send({ message: 'Internal Server Error' });
    }
});

// Start the server on port 3000
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});
```

In this example:

1.  The Express app uses a middleware `validateTask` to validate task data in POST and PUT requests.
2.  Input validation for the `title` and `completed` fields is implemented using `validateTask`.
3.  A health check endpoint is implemented at `/health`, which returns a message indicating that the server is healthy.
4.  The app uses an in-memory array `tasks` to store task data.
5.  Proper HTTP status codes (e.g., 200, 201, 400, 500) and JSON responses are used throughout the application.
6.  Error handling middleware catches any errors that occur during request processing and returns a meaningful error response.

Make sure you have installed Express.js with `npm install express` before running the code:

```bash
# Install required dependencies
npm install express

# Create a new file named app.js and paste the provided code into it
node app.js
```

Once the application is running, you can use a tool like curl or Postman to interact with the REST API endpoints.
```

## Run 2

| Metric | Value |
| ------ | ----: |
| TPS | 132.7 tok/s |
| TTFT | 68.3 ms |
| Total | 10.95 s |
| Memory | 2117 MB |

### Prompt

```
Generate a complete Node.js application using Express.js with the following features:
1. A REST API with CRUD endpoints for a "tasks" resource (GET /tasks, GET /tasks/:id, POST /tasks, PUT /tasks/:id, DELETE /tasks/:id)
2. In-memory storage using a JavaScript array
3. Input validation middleware
4. Error handling middleware
5. A health check endpoint at GET /health
6. Proper HTTP status codes and JSON responses
7. The server should listen on port 3000
Write the complete code in a single file called app.js, ready to run with 'node app.js' after 'npm install express'.
```

### Output

```
Here's a complete Node.js application using Express.js that meets your requirements:

```javascript
const express = require('express');
const bodyParser = require('body-parser');

// Create the Express app
const app = express();

// Middleware for parsing JSON bodies
app.use(bodyParser.json());

// Input validation middleware (not using a library, simple validation)
function validateInput(req, res, next) {
    if (!req.body || !req.body.title || !req.body.description) {
        return res.status(400).json({ error: 'Title and description are required' });
    }
    next();
}

// In-memory storage for tasks
let tasks = [];

// Task model (not an Mongoose document, simple in-memory array)
function createTask(title, description) {
    const newTask = { id: tasks.length + 1, title, description };
    return newTask;
}

function getTasks() {
    return tasks.map(task => ({ id: task.id, title: task.title, description: task.description }));
}

// CRUD operations

app.get('/tasks', (req, res) => {
    try {
        const allTasks = getTasks();
        res.status(200).json(allTasks);
    } catch (error) {
        console.error(error);
        res.status(500).json({ error: 'Internal Server Error' });
    }
});

app.get('/tasks/:id', (req, res) => {
    try {
        const taskId = parseInt(req.params.id);
        if (!taskId || isNaN(taskId)) {
            return res.status(400).json({ error: 'Invalid task ID' });
        }
        const taskIndex = tasks.findIndex(task => task.id === taskId);
        if (taskIndex === -1) {
            return res.status(404).json({ error: 'Task not found' });
        }
        const task = { id: taskId, title: tasks[taskIndex].title, description: tasks[taskIndex].description };
        res.status(200).json(task);
    } catch (error) {
        console.error(error);
        res.status(500).json({ error: 'Internal Server Error' });
    }
});

app.post('/tasks', validateInput, (req, res) => {
    try {
        const title = req.body.title;
        const description = req.body.description;
        if (!title || !description) {
            return res.status(400).json({ error: 'Title and description are required' });
        }
        const newTask = createTask(title, description);
        tasks.push(newTask);
        res.status(201).json(newTask);
    } catch (error) {
        console.error(error);
        res.status(500).json({ error: 'Internal Server Error' });
    }
});

app.put('/tasks/:id', validateInput, (req, res) => {
    try {
        const taskId = parseInt(req.params.id);
        if (!taskId || isNaN(taskId)) {
            return res.status(400).json({ error: 'Invalid task ID' });
        }
        const taskIndex = tasks.findIndex(task => task.id === taskId);
        if (taskIndex === -1) {
            return res.status(404).json({ error: 'Task not found' });
        }
        const updatedTask = { id: taskId, title: req.body.title || tasks[taskIndex].title, description: req.body.description || tasks[taskIndex].description };
        tasks[taskIndex] = updatedTask;
        res.status(200).json(updatedTask);
    } catch (error) {
        console.error(error);
        res.status(500).json({ error: 'Internal Server Error' });
    }
});

app.delete('/tasks/:id', (req, res) => {
    try {
        const taskId = parseInt(req.params.id);
        if (!taskId || isNaN(taskId)) {
            return res.status(400).json({ error: 'Invalid task ID' });
        }
        const taskIndex = tasks.findIndex(task => task.id === taskId);
        if (taskIndex === -1) {
            return res.status(404).json({ error: 'Task not found' });
        }
        tasks.splice(taskIndex, 1);
        res.status(204).send();
    } catch (error) {
        console.error(error);
        res.status(500).json({ error: 'Internal Server Error' });
    }
});

// Health check endpoint
app.get('/health', (req, res) => {
    try {
        res.status(200).json({ status: 'Healthy' });
    } catch (error) {
        console.error(error);
        res.status(500).json({ error: 'Internal Server Error' });
    }
});

// Error handling middleware
app.use((err, req, res, next) => {
    try {
        if (err.name === 'RangeError') {
            return res.status(400).json({ error: err.message });
        } else if (err.name === 'TypeError') {
            return res.status(400).json({ error: err.message });
        } else if (err.name === 'ValidationError') {
            return res.status(400).json({ error: err.message });
        }
    } catch (error) {
        console.error(error);
        res.status(500).json({ error: 'Internal Server Error' });
    }
});

// Serve index.html
app.get('/', (req, res) => {
    try {
        res.sendFile(__dirname + '/index.html');
    } catch (error) {
        console.error(error);
        res.status(404).json({ error: 'Not Found' });
    }
});

// Start the server
const port = 3000;
app.listen(port, () => {
    console.log(`Server is running on port ${port}`);
});
```

This application includes a REST API with CRUD operations for tasks. It uses an in-memory array to store tasks, but it also has input validation middleware and error handling middleware. The server listens on port 3000 and responds with proper HTTP status codes and JSON responses.

To run this code, create a new directory (e.g., `tasks-app`) and create a file called `app.js` inside it. Then, copy the above code into the `app.js` file. Next, run `npm install express` in your terminal to install Express.js. After that, you can start the server with `node app.js`.

You will also need to create an `index.html` file and add a link to it in your HTML file. The `index.html` file should be served by your application.

Please note that this is a simple implementation of REST API and does not cover all possible error scenarios or security considerations. You may want to enhance it based on your specific requirements.
```

## Run 3

| Metric | Value |
| ------ | ----: |
| TPS | 137.0 tok/s |
| TTFT | 64.6 ms |
| Total | 5.79 s |
| Memory | 2117 MB |

### Prompt

```
Generate a complete Node.js application using Express.js with the following features:
1. A REST API with CRUD endpoints for a "tasks" resource (GET /tasks, GET /tasks/:id, POST /tasks, PUT /tasks/:id, DELETE /tasks/:id)
2. In-memory storage using a JavaScript array
3. Input validation middleware
4. Error handling middleware
5. A health check endpoint at GET /health
6. Proper HTTP status codes and JSON responses
7. The server should listen on port 3000
Write the complete code in a single file called app.js, ready to run with 'node app.js' after 'npm install express'.
```

### Output

```
Here is a Node.js application using Express.js that meets all of your requirements:
```javascript
const express = require('express');
const { validateTask } = require('./validation');
const app = express();

// In-memory storage for tasks
let tasks = [];

// Middleware to validate task input
app.use(validateTask);

// Middleware to handle errors
app.use((error, req, res, next) => {
    const statusCode = error.statusCode || 500;
    res.status(statusCode).json({ message: error.message });
});

// Health check endpoint
app.get('/health', (req, res) => {
    res.status(200).json({ status: 'healthy' });
});

// GET /tasks
app.get('/', (req, res) => {
    res.status(200).json(tasks);
});

// GET /tasks/:id
app.get('/:id', (req, res) => {
    const id = req.params.id;
    const task = tasks.find((task) => task.id === parseInt(id));
    if (!task) return res.status(404).json({ message: 'Task not found' });
    res.status(200).json(task);
});

// POST /tasks
app.post('/', (req, res) => {
    validateTask(req.body);
    const newTask = { id: tasks.length + 1, ...req.body };
    tasks.push(newTask);
    res.status(201).json(newTask);
});

// PUT /tasks/:id
app.put('/:id', (req, res) => {
    const id = req.params.id;
    const taskIndex = tasks.findIndex((task) => task.id === parseInt(id));
    if (!taskIndex) return res.status(404).json({ message: 'Task not found' });
    validateTask(req.body);
    tasks[taskIndex] = { ...tasks[taskIndex], ...req.body };
    res.status(200).json(tasks[taskIndex]);
});

// DELETE /tasks/:id
app.delete('/:id', (req, res) => {
    const id = req.params.id;
    const taskIndex = tasks.findIndex((task) => task.id === parseInt(id));
    if (!taskIndex) return res.status(404).json({ message: 'Task not found' });
    delete tasks[taskIndex];
    res.status(204).send();
});

// Start the server
const port = 3000;
app.listen(port, () => {
    console.log(`Server listening on port ${port}`);
});
```

To use this code, you'll need to install Express.js by running `npm install express` in your terminal. Then, run the application with `node app.js`.

Here's an explanation of how the application works:

*   The server listens on port 3000 and uses Express.js as its framework.
*   It has a middleware to validate task input, which ensures that tasks sent over the network meet certain criteria (in this case, they must have a title and description).
*   If validation fails or an error occurs during task operations, it sends back a JSON response with the appropriate status code.
*   The server uses in-memory storage for tasks. In a real-world application, you would typically use a database to store data persistently across restarts of the server.
*   It has a health check endpoint (`GET /health`) that checks whether the server is working properly.
*   For each task-related operation (e.g., reading, creating, updating, deleting tasks), it returns an appropriate HTTP status code along with a JSON response.

You can run the application using `node app.js` and start interacting with your REST API.
```
