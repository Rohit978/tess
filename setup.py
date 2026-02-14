from setuptools import setup, find_packages

setup(
    name="tess-terminal-pro",
    version="5.0.0",
    description="The Hybrid AI Terminal Agent",
    author="Rohit Kumar",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "openai",
        "groq",
        "google-generativeai",
        "chromadb",
        "pydantic",
        "python-dotenv",
        "requests",
        "beautifulsoup4",
        "playwright",
        "pyautogui",
        "Pillow",
        "rich",
        "watchdog",
        "schedule",
        "psutil"
    ],
    entry_points={
        'console_scripts': [
            'tess=tess_cli.cli:main',
        ],
    },
)
