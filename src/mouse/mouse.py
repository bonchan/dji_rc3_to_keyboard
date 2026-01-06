from pynput.mouse import Controller, Button
from enum import Enum

class MouseAxis(Enum):
    ZOOM = 'scroll'

class MouseEmulator:
    def __init__(self, emulate_hardware=True, print_events=True):
        self.mouse = Controller()
        self.emulate_hardware = emulate_hardware
        self.print_events = print_events

    def ZOOM(self, steps):
        """
        Emula el scroll vertical. 
        steps puede ser decimal (ej. 0.1) para scroll suave.
        """
        if abs(steps) < 0.01: # Pequeño umbral de seguridad
            return
            
        if self.print_events: 
            print(f'[MOUSE ZOOM]: {steps:.2f}')
            
        if self.emulate_hardware:
            # pynput.mouse.scroll(dx, dy)
            # dy es el scroll vertical. Positivo es arriba, negativo abajo.
            self.mouse.scroll(0, steps)
    def cleanup(self):
        """
        Libera solo los botones que el emulador sabe que están presionados.
        """
        for button, is_pressed in list(self.active_buttons.items()):
            if is_pressed:
                self._release(button)
                self.active_buttons[button] = False

    def force_cleanup(self):
        """
        Hard reset: Fuerza la liberación de todos los botones posibles del mouse
        en el sistema operativo, sin importar el estado registrado.
        """
        if self.print_events:
            print("[EMERGENCY] Force releasing all mouse buttons...")
            
        # Intentamos liberar cada botón definido en MouseAxis
        for btn in MouseAxis:
            try:
                # Llamamos directamente al controlador de pynput
                self.mouse.release(btn.value)
                self.active_buttons[btn.value] = False
            except Exception:
                # Fallo silencioso si el botón no estaba presionado
                pass
        
        if self.print_events:
            print("[CLEANUP] Mouse reset complete.")