#This agent is built on a defense strategy, prioritizing piece protection and counter attacks.
#This agent evaluates the state of the board, making moves that minimise risk and maximise the potential for counter play. 

import base_agent
import time
import os
import chess
import pygame
from engine import search
from gui import app

ChessAgent = base_agent.BaseAgent

