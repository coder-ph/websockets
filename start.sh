#!/bin/bash
gunicorn -k eventlet -w 1 app:app