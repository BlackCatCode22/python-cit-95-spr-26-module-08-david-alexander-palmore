[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/mZZxJLxL)
# tPythonModule08spr26
tPythonModule08spr26

The Vibe Coding Revolution
Course: CIT-95 - Python Programming (FastAPI)
Professor: Dennis H. Mohle
1. The Mission

You’ve mastered the fundamentals. You’ve tackled the Zoo Keeper Challenge. Now, you are ready for the professional world of Vibe Coding.

Vibe coding is a modern software development practice where you act as the Architect. Instead of getting bogged down in syntax errors, you guide a high-powered AI assistant (Gemini) through a conversational loop to generate, refine, and deploy full-stack applications. This is a real industry shift—in 2026, the best Python developers use these tools to build complex apps in minutes rather than days.

2. Tech Concepts: JSON & Dependencies

In this lab, we use FastAPI, and we rely on two critical industry concepts:

JSON (JavaScript Object Notation): The "language of the internet." When your Python app asks a government server for weather, it receives a raw, structured text format called JSON. You will learn to "parse" this into a Python dictionary.

Dependencies & PIP: You don't have to write your own web server or networking protocols. We use PIP (Python's Package Installer) to download "Dependencies"—pre-written libraries like fastapi, uvicorn, and requests. This saves you from writing thousands of lines of boilerplate code.

3. Step One: Your AI "Brain" (AI Studio)

Go to aistudio.google.com.

Sign in with your Google account.

API Key: On the left sidebar, click "Get API Key." This key allows your local code to talk to the AI. (Free for students!)

4. The "Vibe" Workflow: Baby Steps
Task A: The Fresno/NY JSON Fetch

The National Weather Service (NWS) is free, but they require you to identify your app with a "User-Agent" header.

The Prompt for Gemini:

"I am a Python student using FastAPI. Help me write a script that uses the requests library to fetch current weather JSON from the National Weather Service (api.weather.gov) for Fresno, CA and New York, NY. I want to see the raw JSON printed in my terminal. Use 'FCC-Student-App' as the User-Agent."

Task B: The Human-Readable Web Dashboard

Now, let's turn that data into a real website running on your machine.

The Prompt for Gemini:

"Now, take that weather logic and create a FastAPI web server. Create a route for localhost:8000 that returns a professional HTML page with CSS. Use Python to parse the JSON and display the temperature and conditions for Fresno and New York in a clean, high-end dashboard format."

5. The Digital Handshake: Ngrok

In a Face-to-Face class, we’d just look at your neighbor's IP. Since we are online, your "localhost" is invisible—unless we use a tunnel.

Download Ngrok (ngrok.com).

Run your FastAPI app (usually on port 8000).

In your terminal, type: ngrok http 8000.

The Magic: Ngrok gives you a public URL (e.g., https://python-fresno.ngrok-free.app).

Post your URL in the Canvas Discussion board! Visit your classmates' links to see their live Python dashboards.

6. 🌟 Bonus Opportunity: "London Calling" (+5 Points)

The NWS only covers the US. To go global, you'll use the Open-Meteo API.

The Task: "Vibe" an integration with api.open-meteo.com (no API key needed).

The Goal: Add London, UK to your dashboard. This proves you can handle multiple international data sources.

Submission Requirements:

Code: Your main.py and requirements.txt.

The Link: Post your Ngrok URL to the Canvas thread.

The "Vibe" Reflection (Discusion Post): How did Vibe Coding change your approach to building a "Full Stack" app?
