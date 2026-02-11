#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST CAPTCHA - Prueba de detección de error y refresco de captcha
"""
import sys, time, logging

try:
    from botasaurus.browser import browser, Driver
except ImportError:
    print("[!] pip install botasaurus")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger("TEST_CAPTCHA")

class CaptchaTest:
    URL = "https://titulosinstitutos.minedu.gob.pe/"
    
    def detectar_error_captcha(self, driver: Driver) -> dict:
        """Detecta si hay error de captcha usando el toast message"""
        log.info("═══ DETECTANDO ERROR DE CAPTCHA ═══")
        
        error_info = driver.run_js("""
            var result = {
                hay_error: false,
                mensaje: '',
                toast_visible: false,
                validacion: ''
            };
            
            // 1. Verificar toast-message (el error que aparece y desaparece)
            var toast = document.querySelector('.toast-message');
            if (toast && toast.offsetParent !== null) {
                result.hay_error = true;
                result.toast_visible = true;
                result.mensaje = toast.innerText.trim();
                return result;
            }
            
            // 2. Verificar toast-container (aunque esté oculto)
            var toastContainer = document.querySelector('#toast-container');
            if (toastContainer) {
                var toastMsg = toastContainer.querySelector('.toast-message');
                if (toastMsg) {
                    var txt = toastMsg.innerText.trim();
                    if (txt) {
                        result.hay_error = true;
                        result.mensaje = txt;
                    }
                }
            }
            
            // 3. Verificar span de validación del campo
            var validation = document.querySelector('span[data-valmsg-for="CaptchaCodeText"]');
            if (validation && validation.innerText) {
                result.hay_error = true;
                result.validacion = validation.innerText.trim();
            }
            
            // 4. Verificar alerts
            var alerts = document.querySelectorAll('.alert-danger, .alert-warning');
            for (var i = 0; i < alerts.length; i++) {
                var txt = alerts[i].innerText.toLowerCase();
                if (txt.includes('captcha') || txt.includes('código') || txt.includes('verificación')) {
                    result.hay_error = true;
                    if (!result.mensaje) result.mensaje = alerts[i].innerText.trim();
                }
            }
            
            return result;
        """)
        
        if error_info['hay_error']:
            log.error(f"❌ ERROR DETECTADO!")
            log.error(f"   Toast visible: {error_info['toast_visible']}")
            log.error(f"   Mensaje: {error_info['mensaje']}")
            log.error(f"   Validación: {error_info['validacion']}")
        else:
            log.info("✓ No se detectó error de captcha")
            
        return error_info
    
    def refrescar_captcha(self, driver: Driver) -> bool:
        """Refresca el captcha usando el botón en lugar de recargar la página"""
        log.info("═══ REFRESCANDO CAPTCHA ═══")
        
        try:
            # Hacer click en el botón de refresh
            clicked = driver.run_js("""
                var btn = document.querySelector('#CapImageRefresh');
                if (btn) {
                    console.log('Botón encontrado, haciendo click...');
                    btn.click();
                    return true;
                }
                console.log('Botón NO encontrado');
                return false;
            """)
            
            if clicked:
                log.info("✓ Click en botón de refresh exitoso")
                time.sleep(1.5)  # Esperar a que cargue nueva imagen
                
                # Verificar que la imagen cambió
                nueva_imagen = driver.run_js("""
                    var img = document.querySelector('#imgCaptcha');
                    return img ? img.src.substring(0, 50) + '...' : null;
                """)
                log.info(f"✓ Nueva imagen captcha: {nueva_imagen}")
                
                return True
            else:
                log.error("❌ No se pudo hacer click en el botón de refresh")
                return False
                
        except Exception as e:
            log.error(f"❌ Error al refrescar captcha: {e}")
            return False
    
    def probar_flujo_completo(self, driver: Driver, dni: str = "10777845"):
        """Prueba el flujo completo: capcha malo → detectar → refrescar → captcha correcto"""
        log.info("═══ PASO 1: INGRESAR DNI ═══")
        
        driver.run_js(f"""
            var dni = document.querySelector('#DOCU_NUM');
            if (dni) {{
                dni.value = '{dni}';
                dni.dispatchEvent(new Event('input', {{ bubbles: true }}));
                dni.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
        """)
        log.info(f"✓ DNI ingresado: {dni}")
        time.sleep(1)
        
        log.info("═══ PASO 2: INGRESAR CAPTCHA MALO (PARA PROBAR) ═══")
        captcha_malo = "XXXXX"
        
        driver.run_js(f"""
            var cap = document.querySelector('#CaptchaCodeText');
            if (cap) {{
                cap.removeAttribute('disabled');
                cap.disabled = false;
                cap.value = '{captcha_malo}';
                cap.dispatchEvent(new Event('input', {{ bubbles: true }}));
                cap.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
        """)
        log.info(f"✓ Captcha incorrecto ingresado: {captcha_malo}")
        time.sleep(1)
        
        driver.run_js("""
            var btn = document.querySelector('#btnConsultar');
            if (btn) {
                btn.removeAttribute('disabled');
                btn.disabled = false;
                btn.classList.remove('inactivo');
                btn.click();
            }
        """)
        log.info("✓ Click en buscar")
        time.sleep(3)
        
        log.info("═══ PASO 3: INTENTAR RESOLVER CON CAPTCHA CORRECTO (Máx 3 intentos) ═══")
        
        for intento in range(1, 4):
            log.info(f"\n[Intento {intento}/3]")
            
            # Detectar error
            error = self.detectar_error_captcha(driver)
            
            if error['hay_error']:
                log.warning(f"❌ Error detectado: {error['mensaje'][:60]}")
                
                # Refrescar captcha
                log.info("[↻] Refrescando captcha...")
                if not self.refrescar_captcha(driver):
                    log.error("❌ Fallo al refrescar")
                    continue
                    
                time.sleep(1.5)
                
                # Resolver con OCR
                import ddddocr, base64
                ocr = ddddocr.DdddOcr(show_ad=False)
                
                b64 = driver.run_js("""
                    var img = document.querySelector('#imgCaptcha');
                    return img ? img.src : null;
                """)
                
                if not b64 or "base64," not in b64:
                    log.error("❌ No se pudo obtener imagen")
                    continue
                    
                b64 = b64.split("base64,")[1]
                img_bytes = base64.b64decode(b64)
                captcha_correcto = ocr.classification(img_bytes)
                
                log.info(f"[OCR] Resultado: {captcha_correcto}")
                
                # Ingresar captcha correcto
                driver.run_js(f"""
                    var cap = document.querySelector('#CaptchaCodeText');
                    if (cap) {{
                        cap.value = '{captcha_correcto}';
                        cap.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        cap.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                """)
                
                time.sleep(0.5)
                
                # Click buscar
                driver.run_js("""
                    var btn = document.querySelector('#btnConsultar');
                    if (btn) {
                        btn.disabled = false;
                        btn.classList.remove('inactivo');
                        btn.click();
                    }
                """)
                
                log.info("✓ Captcha enviado")
                time.sleep(3)
                
                # Verificar resultado
                error2 = self.detectar_error_captcha(driver)
                if error2['hay_error']:
                    log.warning(f"[!] Aún hay error en intento {intento}/3")
                    continue
                else:
                    resultado_html = driver.run_js("""
                        var div = document.querySelector('#divResultado');
                        return div ? div.innerHTML.length : 0;
                    """)
                    
                    if resultado_html > 50:
                        log.info("✓✓✓ ÉXITO COMPLETO ✓✓✓")
                        log.info(f"    Resuelto en intento {intento}/3")
                        return True
            else:
                log.info("✓ No hay error, verificando resultados...")
                time.sleep(2)
                
                resultado_html = driver.run_js("""
                    var div = document.querySelector('#divResultado');
                    return div ? div.innerHTML.length : 0;
                """)
                
                if resultado_html > 50:
                    log.info("✓✓✓ ÉXITO ✓✓✓")
                    return True
        
        log.warning("⚠ No se completó después de 3 intentos")
        return False
    
    def ejecutar_prueba(self):
        """Ejecuta la prueba completa"""
        @browser(headless=False, block_images=False, window_size=(1200, 800))
        def test(driver: Driver, data):
            log.info("╔═══════════════════════════════════════════╗")
            log.info("║   PRUEBA DE DETECCIÓN DE ERROR CAPTCHA   ║")
            log.info("╚═══════════════════════════════════════════╝")
            
            driver.get(self.URL)
            time.sleep(3)
            
            # Probar flujo completo
            self.probar_flujo_completo(driver)
            
            log.info("\n╔═══════════════════════════════════════════╗")
            log.info("║          PRUEBA COMPLETADA                ║")
            log.info("╚═══════════════════════════════════════════╝")
            
            input("\nPresiona ENTER para cerrar el navegador...")
            return True
        
        test({})


if __name__ == "__main__":
    print("="*50)
    print("  TEST CAPTCHA - Detección y Refresco")
    print("="*50)
    CaptchaTest().ejecutar_prueba()
    print("[OK] FIN")
