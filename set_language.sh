#!/bin/bash
# Script to change bot language

cd /home/mohirbek/Projects/Impulse

if [ "$1" == "uz" ]; then
    echo "Setting language to Uzbek..."
    sed -i 's/BOT_LANGUAGE=.*/BOT_LANGUAGE=uz/' .env
    echo "✅ Language set to Uzbek (uz)"
elif [ "$1" == "ru" ]; then
    echo "Setting language to Russian..."
    sed -i 's/BOT_LANGUAGE=.*/BOT_LANGUAGE=ru/' .env
    echo "✅ Language set to Russian (ru)"
else
    echo "Usage: ./set_language.sh [uz|ru]"
    echo "Current language setting:"
    grep BOT_LANGUAGE .env || echo "BOT_LANGUAGE not set (default: uz)"
fi
