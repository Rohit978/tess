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
        "pyautogui>=0.9.54",
        "psutil>=5.9.0",
        "pydantic>=2.0.0",
        "watchdog>=3.0.0",
        "pathspec>=0.11.0",
        "sounddevice>=0.4.6",
        "scipy>=1.11.0",
        "openai-whisper>=20231117",
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
