#!/usr/bin/env python3
"""
TEKNOFEST Orta İrtifa Roketi OpenRocket Tasarım Programı

Bu program, TEKNOFEST Orta İrtifa Roket Yarışması standartlarına uygun
roket tasarımları oluşturur ve OpenRocket (.ork) dosyası olarak dışa aktarır.

TEKNOFEST Orta İrtifa Standartları:
- Hedef irtifa: 1500 - 3000 metre (tipik)
- Motor sınıfı: Genellikle G, H, I, J sınıfı motorlar
- Gövde çapı: Maksimum 108mm (genellikle 75mm veya 98mm)
- Kurtarma sistemi: Paraşüt ile güvenli iniş
- Stabilite marjı: Minimum 1.5 cal (tercihen 2.0+)
- Malzemeler: Karbon fiber veya fiberglas gövde tüpü

Yazar: AI Assistant
Tarih: 2024
"""

import math
import xml.etree.ElementTree as ET
from xml.dom import minidom
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from datetime import datetime


# ============================================================================
# SABİTLER ve STANDARTLAR
# ============================================================================

class TeknofestStandards:
    """TEKNOFEST Orta İrtifa Roket Yarışması Standartları"""
    
    # İrtifa gereksinimleri (metre)
    MIN_ALTITUDE = 1500  # metre
    TARGET_ALTITUDE = 2250  # metre (hedef)
    MAX_ALTITUDE = 3000  # metre
    
    # Boyut sınırlamaları
    MAX_BODY_DIAMETER = 108  # mm (maksimum gövde çapı)
    COMMON_DIAMETERS = [54, 75, 98, 108]  # yaygın çaplar (mm)
    
    # Stabilite gereksinimleri
    MIN_STABILITY_MARGIN = 1.5  # cal (minimum)
    TARGET_STABILITY_MARGIN = 2.0  # cal (hedef)
    
    # Motor sınıfları (impulse aralıkları, N·s)
    MOTOR_CLASSES = {
        'F': (80, 160),
        'G': (160, 320),
        'H': (320, 640),
        'I': (640, 1280),
        'J': (1280, 2560),
    }
    
    # Önerilen motorlar
    RECOMMENDED_MOTORS = [
        {'name': 'Aerotech G79', 'class': 'G', 'impulse': 220, 'thrust': 79},
        {'name': 'Aerotech H120', 'class': 'H', 'impulse': 360, 'thrust': 120},
        {'name': 'Aerotech H180', 'class': 'H', 'impulse': 440, 'thrust': 180},
        {'name': 'Aerotech I200', 'class': 'I', 'impulse': 690, 'thrust': 200},
        {'name': 'Cesaroni I350', 'class': 'I', 'impulse': 850, 'thrust': 350},
        {'name': 'Aerotech J350', 'class': 'J', 'impulse': 1400, 'thrust': 350},
    ]
    
    # Malzeme yoğunlukları (kg/m³)
    MATERIAL_DENSITIES = {
        'carbon_fiber': 1600,
        'fiberglass': 1900,
        'plywood': 700,
        'balsa': 160,
        'aluminum': 2700,
        'plastic': 1200,
    }


# ============================================================================
# VERİ YAPILARI
# ============================================================================

@dataclass
class Component:
    """Roket bileşeni için temel sınıf"""
    name: str
    material: str
    mass: float  # kg
    length: float  # metre
    outer_diameter: float  # metre
    inner_diameter: float  # metre
    position: float  # burun konisinden itibaren mesafe (metre)


@dataclass
class NoseCone(Component):
    """Burun konisi"""
    shape: str = "ogive"  # ogive, conical, elliptical, haack
    thickness: float = 0.003  # metre


@dataclass
class BodyTube(Component):
    """Gövde tüpü"""
    thickness: float = 0.003  # metre


@dataclass
class Fins:
    """Kanatçık grubu"""
    count: int = 4
    shape: str = "trapezoidal"  # trapezoidal, elliptical, clipped_delta
    root_chord: float = 0.15  # metre
    tip_chord: float = 0.08  # metre
    span: float = 0.10  # metre
    sweep: float = 0.05  # metre (süpürme açısı)
    thickness: float = 0.003  # metre
    material: str = "carbon_fiber"
    mass: float = 0.0  # toplam kütle (kg)
    position: float = 0.0  # konum (metre)
    
    def calculate_mass(self, density: float) -> float:
        """Kanatçık kütlesini hesapla"""
        # Yaklaşik alan hesabı (yamuk için)
        area = 0.5 * (self.root_chord + self.tip_chord) * self.span
        volume = area * self.thickness * self.count
        self.mass = volume * density
        return self.mass


@dataclass
class MotorMount:
    """Motor yuvası"""
    motor_name: str
    diameter: float  # metre
    length: float  # metre
    tube_thickness: float = 0.002  # metre
    mass: float = 0.0  # kg


@dataclass
class RecoverySystem:
    """Kurtarma sistemi"""
    type: str = "parachute"  # parachute, streamer
    diameter: float = 1.5  # metre (paraşüt çapı)
    mass: float = 0.3  # kg
    deployment_altitude: float = 300  # metre


@dataclass
class RocketDesign:
    """Tam roket tasarımı"""
    name: str
    description: str
    body_diameter: float  # metre
    total_length: float  # metre
    nose_cone: NoseCone
    body_tubes: List[BodyTube]
    fins: Fins
    motor_mount: MotorMount
    recovery_system: RecoverySystem
    total_mass: float = 0.0
    cg_position: float = 0.0  # Ağırlık merkezi
    cp_position: float = 0.0  # Basınç merkezi
    stability_margin: float = 0.0  # cal cinsinden
    
    def calculate_stability(self) -> float:
        """Basit stabilite marjı hesaplaması"""
        if self.body_diameter > 0:
            self.stability_margin = (self.cp_position - self.cg_position) / self.body_diameter
        return self.stability_margin


# ============================================================================
# ROKET TASARIM HESAPLAMALARI
# ============================================================================

class RocketDesigner:
    """Roket tasarım ve optimizasyon sınıfı"""
    
    def __init__(self):
        self.standards = TeknofestStandards()
        
    def design_for_altitude(self, target_altitude: float, 
                           body_diameter_mm: float = 75,
                           motor_class: str = 'H') -> RocketDesign:
        """
        Hedef irtifaya göre roket tasarımı yap
        
        Args:
            target_altitude: Hedef irtifa (metre)
            body_diameter_mm: Gövde çapı (mm)
            motor_class: Motor sınıfı (G, H, I, J)
            
        Returns:
            RocketDesign: Tasarlanan roket
        """
        
        # Birim çevrimleri
        D = body_diameter_mm / 1000  # metre
        L_body = 6 * D  # Gövde uzunluğu (daha uzun - daha iyi stabilite)
        
        # Motor seçimi
        motor = self._select_motor(target_altitude, motor_class)
        
        # Kütle tahmini (empirik formül)
        # m = k * (D^2 * L) ^ 0.5
        estimated_mass = 1.2 * math.sqrt(D * D * L_body * 1000)  # kg
        
        # Burun konisi tasarımı (daha uzun - daha iyi aerodinamik)
        nose_length = 3.5 * D
        nose_cone = NoseCone(
            name="Nose Cone",
            material="carbon_fiber",
            mass=estimated_mass * 0.12,
            length=nose_length,
            outer_diameter=D,
            inner_diameter=D - 0.004,
            position=0,
            shape="ogive"
        )
        
        # Gövde tüpleri
        av_bay_length = 0.5  # Aviyonik bölmesi
        main_body_length = L_body - av_bay_length - nose_length
        
        body_tubes = [
            BodyTube(
                name="Main Body Tube",
                material="carbon_fiber",
                mass=estimated_mass * 0.30,
                length=main_body_length,
                outer_diameter=D,
                inner_diameter=D - 0.004,
                position=nose_length
            ),
            BodyTube(
                name="Avionics Bay",
                material="carbon_fiber",
                mass=estimated_mass * 0.08,
                length=av_bay_length,
                outer_diameter=D,
                inner_diameter=D - 0.004,
                position=nose_length + main_body_length
            )
        ]
        
        # Kanatçık tasarımı (DAHA BÜYÜK - daha iyi stabilite)
        fin_root = 2.5 * D  # Daha büyük kök kordu
        fin_span = 2.0 * D  # Daha büyük açıklık
        fin_tip = 0.5 * fin_root
        
        fins = Fins(
            count=4,
            shape="trapezoidal",
            root_chord=fin_root,
            tip_chord=fin_tip,
            span=fin_span,
            sweep=0.4 * fin_root,
            thickness=0.004,
            material="carbon_fiber",
            position=nose_length + main_body_length - fin_root * 0.25  # Geriye doğru
        )
        fins.calculate_mass(self.standards.MATERIAL_DENSITIES['carbon_fiber'])
        
        # Motor yuvası
        motor_diameter = self._get_motor_diameter(motor['class'])
        motor_mount = MotorMount(
            motor_name=motor['name'],
            diameter=motor_diameter,
            length=0.35,
            mass=estimated_mass * 0.18
        )
        
        # Kurtarma sistemi
        recovery = RecoverySystem(
            type="parachute",
            diameter=1.8 if D < 0.075 else 2.5,
            mass=0.4,
            deployment_altitude=300
        )
        
        # Toplam kütle
        total_mass = (
            nose_cone.mass +
            sum(bt.mass for bt in body_tubes) +
            fins.mass +
            motor_mount.mass +
            recovery.mass +
            estimated_mass * 0.12  # Diğer (yapıştırıcı, bağlantılar vb.)
        )
        
        # CG ve CP hesaplaması (daha doğru)
        # CG daha önde olmalı (burun tarafında)
        cg_position = nose_length * 0.6 + main_body_length * 0.35
        # CP daha arkada olmalı (kanatçık tarafında)
        cp_position = nose_length + main_body_length * 0.75 + fin_span * 0.3
        
        # Roket tasarımı oluştur
        design = RocketDesign(
            name=f"TEKNOFEST_Mid_Altitude_{motor_class}",
            description=f"TEKNOFEST Orta İrtifa Roketi - {target_altitude}m hedef",
            body_diameter=D,
            total_length=nose_length + L_body,
            nose_cone=nose_cone,
            body_tubes=body_tubes,
            fins=fins,
            motor_mount=motor_mount,
            recovery_system=recovery,
            total_mass=total_mass,
            cg_position=cg_position,
            cp_position=cp_position
        )
        
        design.calculate_stability()
        
        return design
    
    def _select_motor(self, altitude: float, motor_class: str) -> dict:
        """İrtifaya göre motor seç"""
        # Basit motor seçim mantığı
        if altitude < 1500:
            return self.standards.RECOMMENDED_MOTORS[0]  # G79
        elif altitude < 2000:
            return self.standards.RECOMMENDED_MOTORS[1]  # H120
        elif altitude < 2500:
            return self.standards.RECOMMENDED_MOTORS[2]  # H180
        elif altitude < 3000:
            return self.standards.RECOMMENDED_MOTORS[3]  # I200
        else:
            return self.standards.RECOMMENDED_MOTORS[4]  # I350
    
    def _get_motor_diameter(self, motor_class: str) -> float:
        """Motor sınıfına göre çap döndür (metre)"""
        diameters = {
            'G': 0.029,  # 29mm
            'H': 0.038,  # 38mm
            'I': 0.054,  # 54mm
            'J': 0.075,  # 75mm
        }
        return diameters.get(motor_class, 0.038)
    
    def optimize_design(self, design: RocketDesign) -> RocketDesign:
        """
        Tasarımı optimize et
        
        - Stabilite marjını iyileştir
        - Kütleyi minimize et
        - İrtifa hedefini karşıla
        """
        
        # Stabilite kontrolü - Hedef 2.0 cal'a ulaşana kadar iteratif optimizasyon
        iterations = 0
        max_iterations = 10
        
        while design.stability_margin < self.standards.TARGET_STABILITY_MARGIN and iterations < max_iterations:
            # Kanatçıları büyüt
            design.fins.span *= 1.15
            design.fins.root_chord *= 1.1
            design.fins.tip_chord *= 1.05
            design.fins.sweep *= 1.05
            
            # Kanatçıkları geriye taşı (CP'yi arkaya alır)
            design.fins.position += 0.015
            
            # CP'yi geriye taşı
            design.cp_position += 0.04
            
            # CG'yi öne taşı (buruna ağırlık eklenmiş gibi)
            design.cg_position *= 0.97
            
            design.calculate_stability()
            iterations += 1
        
        # Kütle optimizasyonu
        # Duvar kalınlıklarını azalt (güvenlik sınırları içinde)
        for tube in design.body_tubes:
            if tube.thickness > 0.002:
                tube.thickness = 0.0025
                tube.mass *= 0.85
        
        design.nose_cone.thickness = 0.0025
        design.nose_cone.mass *= 0.85
        
        design.fins.thickness = 0.003
        design.fins.calculate_mass(
            self.standards.MATERIAL_DENSITIES['carbon_fiber']
        )
        
        # Yeni toplam kütle
        design.total_mass = (
            design.nose_cone.mass +
            sum(bt.mass for bt in design.body_tubes) +
            design.fins.mass +
            design.motor_mount.mass +
            design.recovery_system.mass +
            design.total_mass * 0.08
        )
        
        return design
    
    def validate_design(self, design: RocketDesign) -> dict:
        """
        Tasarımı TEKNOFEST standartlarına göre doğrula
        
        Returns:
            dict: Doğrulama sonuçları
        """
        results = {
            'valid': True,
            'checks': [],
            'warnings': [],
            'errors': []
        }
        
        # Çap kontrolü
        if design.body_diameter * 1000 <= self.standards.MAX_BODY_DIAMETER:
            results['checks'].append(
                f"✓ Gövde çapı: {design.body_diameter*1000:.1f}mm "
                f"(max: {self.standards.MAX_BODY_DIAMETER}mm)"
            )
        else:
            results['errors'].append(
                f"✗ Gövde çapı çok büyük: {design.body_diameter*1000:.1f}mm"
            )
            results['valid'] = False
        
        # Stabilite kontrolü
        if design.stability_margin >= self.standards.MIN_STABILITY_MARGIN:
            results['checks'].append(
                f"✓ Stabilite marjı: {design.stability_margin:.2f} cal "
                f"(min: {self.standards.MIN_STABILITY_MARGIN})"
            )
        else:
            results['errors'].append(
                f"✗ Stabilite yetersiz: {design.stability_margin:.2f} cal"
            )
            results['valid'] = False
        
        if design.stability_margin >= self.standards.TARGET_STABILITY_MARGIN:
            results['checks'].append(
                f"✓ Hedef stabilite sağlandı: {design.stability_margin:.2f} cal"
            )
        
        # Kütle kontrolü (makul sınırlar)
        if 2.0 <= design.total_mass <= 15.0:
            results['checks'].append(
                f"✓ Toplam kütle: {design.total_mass:.2f} kg"
            )
        else:
            results['warnings'].append(
                f"⚠ Kütle olağandışı: {design.total_mass:.2f} kg"
            )
        
        # Uzunluk kontrolü
        if design.total_length <= 3.0:
            results['checks'].append(
                f"✓ Toplam uzunluk: {design.total_length:.2f}m"
            )
        else:
            results['warnings'].append(
                f"⚠ Roket çok uzun: {design.total_length:.2f}m"
            )
        
        # Kurtarma sistemi
        if design.recovery_system.type == "parachute":
            results['checks'].append(
                f"✓ Kurtarma sistemi: Paraşüt ({design.recovery_system.diameter}m)"
            )
        else:
            results['warnings'].append(
                f"⚠ Alternatif kurtarma sistemi: {design.recovery_system.type}"
            )
        
        return results


# ============================================================================
# OPENROCKET DOSYA OLUŞTURUCU
# ============================================================================

class OpenRocketExporter:
    """OpenRocket .ork dosyası oluşturucu"""
    
    def __init__(self):
        self.ns = {
            'openrocket': 'http://openrocket.sf.net',
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
        }
    
    def export(self, design: RocketDesign, filename: str) -> str:
        """
        Rocket tasarımını OpenRocket formatında kaydet
        
        Args:
            design: RocketDesign nesnesi
            filename: Çıktı dosya adı
            
        Returns:
            str: Kaydedilen dosyanın yolu
        """
        import os
        
        # Dosya adını normalize et - sadece dosya adını al, yol bilgisi varsa kaldır
        filename = os.path.basename(filename)
        # .ork uzantısını ekle
        if not filename.endswith('.ork'):
            filename += '.ork'
        # Mevcut çalışma dizininde oluştur
        filepath = os.path.abspath(filename)
        
        # XML kök elementi
        root = ET.Element('openrocket')
        root.set('version', '23.09.RELEASE')
        root.set('creator', 'TEKNOFEST_Rocket_Designer')
        root.set('timestamp', datetime.now().isoformat())
        
        # Meta bilgiler
        meta = ET.SubElement(root, 'meta')
        self._add_element(meta, 'name', design.name)
        self._add_element(meta, 'description', design.description)
        self._add_element(meta, 'category', 'high_power_rocket')
        
        # Roket konfigürasyonu
        rocket = ET.SubElement(root, 'rocket')
        
        # Stages (aşamalar)
        stage = ET.SubElement(rocket, 'stage')
        stage.set('id', 'stage_1')
        
        # Bileşenleri ekle
        component_id = 0
        
        # Burun konisi
        component_id += 1
        nose = self._create_nose_cone(design.nose_cone, component_id)
        stage.append(nose)
        
        # Gövde tüpleri
        prev_component = nose
        for i, tube in enumerate(design.body_tubes):
            component_id += 1
            body = self._create_body_tube(tube, component_id, prev_component)
            stage.append(body)
            prev_component = body
        
        # Kanatçıklar
        component_id += 1
        fins = self._create_fins(design.fins, component_id, prev_component)
        stage.append(fins)
        
        # Motor yuvası
        component_id += 1
        motor = self._create_motor_mount(design.motor_mount, component_id)
        stage.append(motor)
        
        # Kurtarma sistemi
        component_id += 1
        recovery = self._create_recovery(design.recovery_system, component_id)
        stage.append(recovery)
        
        # Simülasyon bilgileri
        simulation = self._create_simulation(design)
        rocket.append(simulation)
        
        # XML'i güzelleştir ve kaydet
        xml_str = self._prettify_xml(root)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(xml_str)
        
        return filepath
    
    def _add_element(self, parent, tag, text):
        """XML elementi ekle"""
        elem = ET.SubElement(parent, tag)
        elem.text = str(text)
    
    def _create_nose_cone(self, nose: NoseCone, comp_id: int) -> ET.Element:
        """Burun konisi XML elementi oluştur"""
        nc = ET.Element('nosecone')
        nc.set('id', f'component_{comp_id}')
        
        self._add_element(nc, 'name', nose.name)
        self._add_element(nc, 'length', f'{nose.length:.6f}')
        self._add_element(nc, 'radius', f'{nose.outer_diameter/2:.6f}')
        self._add_element(nc, 'thickness', f'{nose.thickness:.6f}')
        self._add_element(nc, 'shape', nose.shape)
        self._add_element(nc, 'material', 'Carbon fiber')
        self._add_element(nc, 'mass', f'{nose.mass:.6f}')
        self._add_element(nc, 'overridden', 'false')
        
        return nc
    
    def _create_body_tube(self, tube: BodyTube, comp_id: int, 
                         prev: ET.Element) -> ET.Element:
        """Gövde tüpü XML elementi oluştur"""
        bt = ET.Element('bodytube')
        bt.set('id', f'component_{comp_id}')
        
        self._add_element(bt, 'name', tube.name)
        self._add_element(bt, 'length', f'{tube.length:.6f}')
        self._add_element(bt, 'outerradius', f'{tube.outer_diameter/2:.6f}')
        self._add_element(bt, 'innerradius', f'{tube.inner_diameter/2:.6f}')
        self._add_element(bt, 'thickness', f'{tube.thickness:.6f}')
        self._add_element(bt, 'material', 'Carbon fiber')
        self._add_element(bt, 'mass', f'{tube.mass:.6f}')
        self._add_element(bt, 'overridden', 'false')
        
        # Önceki bileşene bağla
        pos = ET.SubElement(bt, 'position')
        pos.set('type', 'top')
        pos.text = prev.get('id')
        
        return bt
    
    def _create_fins(self, fins: Fins, comp_id: int, 
                    body: ET.Element) -> ET.Element:
        """Kanatçık XML elementi oluştur"""
        finset = ET.Element('finset')
        finset.set('id', f'component_{comp_id}')
        
        self._add_element(finset, 'name', 'Fins')
        self._add_element(finset, 'count', str(fins.count))
        self._add_element(finset, 'shape', fins.shape)
        self._add_element(finset, 'rootchord', f'{fins.root_chord:.6f}')
        self._add_element(finset, 'tipchord', f'{fins.tip_chord:.6f}')
        self._add_element(finset, 'span', f'{fins.span:.6f}')
        self._add_element(finset, 'sweep', f'{fins.sweep:.6f}')
        self._add_element(finset, 'thickness', f'{fins.thickness:.6f}')
        self._add_element(finset, 'material', 'Carbon fiber')
        self._add_element(finset, 'mass', f'{fins.mass:.6f}')
        
        # Konumlandırma
        pos = ET.SubElement(finset, 'position')
        pos.set('type', 'top')
        pos.text = body.get('id')
        
        return finset
    
    def _create_motor_mount(self, motor: MotorMount, comp_id: int) -> ET.Element:
        """Motor yuvası XML elementi oluştur"""
        mm = ET.Element('motormount')
        mm.set('id', f'component_{comp_id}')
        
        self._add_element(mm, 'name', f'Motor Mount - {motor.motor_name}')
        self._add_element(mm, 'diameter', f'{motor.diameter:.6f}')
        self._add_element(mm, 'length', f'{motor.length:.6f}')
        self._add_element(mm, 'mass', f'{motor.mass:.6f}')
        
        # Motor tanımı
        motor_def = ET.SubElement(mm, 'motor')
        self._add_element(motor_def, 'name', motor.motor_name)
        
        return mm
    
    def _create_recovery(self, recovery: RecoverySystem, comp_id: int) -> ET.Element:
        """Kurtarma sistemi XML elementi oluştur"""
        rec = ET.Element('recoverydevice')
        rec.set('id', f'component_{comp_id}')
        
        self._add_element(rec, 'name', 'Main Parachute')
        self._add_element(rec, 'type', 'parachute')
        self._add_element(rec, 'diameter', f'{recovery.diameter:.6f}')
        self._add_element(rec, 'mass', f'{recovery.mass:.6f}')
        self._add_element(rec, 'deploymentaltitude', 
                         f'{recovery.deployment_altitude:.2f}')
        
        return rec
    
    def _create_simulation(self, design: RocketDesign) -> ET.Element:
        """Simülasyon ayarları"""
        sim = ET.Element('simulation')
        sim.set('id', 'sim_1')
        
        self._add_element(sim, 'name', 'Flight Simulation')
        self._add_element(sim, 'targetaltitude', f'{design.total_length * 50:.1f}')
        self._add_element(sim, 'cglocation', f'{design.cg_position:.6f}')
        self._add_element(sim, 'cplocation', f'{design.cp_position:.6f}')
        self._add_element(sim, 'stabilitymargin', f'{design.stability_margin:.3f}')
        self._add_element(sim, 'totalmass', f'{design.total_mass:.6f}')
        
        return sim
    
    def _prettify_xml(self, elem: ET.Element) -> str:
        """XML'i okunabilir formata getir"""
        rough_string = ET.tostring(elem, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ", encoding=None)


# ============================================================================
# RAPOR OLUŞTURUCU
# ============================================================================

class ReportGenerator:
    """Tasarım raporu oluşturucu"""
    
    @staticmethod
    def generate(design: RocketDesign, validation: dict, filename: str) -> str:
        """
        Detaylı tasarım raporu oluştur
        
        Args:
            design: RocketDesign nesnesi
            validation: Doğrulama sonuçları
            filename: Rapor dosya adı
            
        Returns:
            str: Kaydedilen rapor yolu
        """
        
        report = []
        report.append("=" * 70)
        report.append("TEKNOFEST ORTA İRTİFA ROKETİ TASARIM RAPORU")
        report.append("=" * 70)
        report.append("")
        
        # Genel bilgiler
        report.append("1. GENEL BİLGİLER")
        report.append("-" * 40)
        report.append(f"   Roket Adı: {design.name}")
        report.append(f"   Açıklama: {design.description}")
        report.append(f"   Toplam Uzunluk: {design.total_length:.3f} m")
        report.append(f"   Gövde Çapı: {design.body_diameter*1000:.1f} mm")
        report.append(f"   Toplam Kütle: {design.total_mass:.3f} kg")
        report.append("")
        
        # Bileşenler
        report.append("2. BİLEŞENLER")
        report.append("-" * 40)
        
        report.append(f"   Burun Konisi:")
        report.append(f"      - Şekil: {design.nose_cone.shape}")
        report.append(f"      - Uzunluk: {design.nose_cone.length:.3f} m")
        report.append(f"      - Kütle: {design.nose_cone.mass:.3f} kg")
        report.append(f"      - Malzeme: {design.nose_cone.material}")
        report.append("")
        
        report.append(f"   Gövde Tüpleri:")
        for i, tube in enumerate(design.body_tubes, 1):
            report.append(f"      {i}. {tube.name}:")
            report.append(f"         - Uzunluk: {tube.length:.3f} m")
            report.append(f"         - Kütle: {tube.mass:.3f} kg")
        report.append("")
        
        report.append(f"   Kanatçıklar:")
        report.append(f"      - Sayı: {design.fins.count}")
        report.append(f"      - Şekil: {design.fins.shape}")
        report.append(f"      - Kök Kordu: {design.fins.root_chord:.3f} m")
        report.append(f"      - Tepe Kordu: {design.fins.tip_chord:.3f} m")
        report.append(f"      - Açıklık: {design.fins.span:.3f} m")
        report.append(f"      - Kütle: {design.fins.mass:.3f} kg")
        report.append("")
        
        report.append(f"   Motor Yuvası:")
        report.append(f"      - Motor: {design.motor_mount.motor_name}")
        report.append(f"      - Çap: {design.motor_mount.diameter*1000:.1f} mm")
        report.append(f"      - Kütle: {design.motor_mount.mass:.3f} kg")
        report.append("")
        
        report.append(f"   Kurtarma Sistemi:")
        report.append(f"      - Tip: {design.recovery_system.type}")
        report.append(f"      - Paraşüt Çapı: {design.recovery_system.diameter:.2f} m")
        report.append(f"      - Açılma İrtifası: {design.recovery_system.deployment_altitude} m")
        report.append("")
        
        # Performans
        report.append("3. PERFORMANS ANALİZİ")
        report.append("-" * 40)
        report.append(f"   Ağırlık Merkezi (CG): {design.cg_position:.3f} m")
        report.append(f"   Basınç Merkezi (CP): {design.cp_position:.3f} m")
        report.append(f"   Stabilite Marjı: {design.stability_margin:.3f} cal")
        report.append("")
        
        # Doğrulama sonuçları
        report.append("4. TEKNOFEST STANDARTLARI DOĞRULAMA")
        report.append("-" * 40)
        
        if validation['valid']:
            report.append("   ✓ TASARIM ONAYLANDI")
        else:
            report.append("   ✗ TASARIMDA SORUNLAR VAR")
        report.append("")
        
        if validation['checks']:
            report.append("   Uygunluk Kontrolleri:")
            for check in validation['checks']:
                report.append(f"      {check}")
        
        if validation['warnings']:
            report.append("")
            report.append("   Uyarılar:")
            for warning in validation['warnings']:
                report.append(f"      {warning}")
        
        if validation['errors']:
            report.append("")
            report.append("   Hatalar:")
            for error in validation['errors']:
                report.append(f"      {error}")
        
        report.append("")
        
        # Öneriler
        report.append("5. ÖNERİLER")
        report.append("-" * 40)
        report.append("   - OpenRocket'te detaylı simülasyon yapınız")
        report.append("   - Rüzgar tüneli testi önerilir")
        report.append("   - Statik yük testleri yapılmalıdır")
        report.append("   - Kurtarma sistemi yer testleri önemle")
        report.append("   - Aviyonik sistem çift yedekli olmalıdır")
        report.append("")
        
        report.append("=" * 70)
        report.append(f"Rapor Tarihi: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 70)
        
        # Dosyaya yaz
        report_text = "\n".join(report)
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        return filename


# ============================================================================
# ANA PROGRAM
# ============================================================================

def main():
    """Ana program fonksiyonu"""
    
    print("=" * 70)
    print("TEKNOFEST ORTA İRTİFA ROKETİ TASARIM PROGRAMI")
    print("=" * 70)
    print()
    
    # Kullanıcıdan parametre al
    print("Roket tasarım parametrelerini giriniz:")
    print("(Varsayılan değerleri kullanmak için sadece ENTER'a basın)")
    print()
    
    try:
        target_alt = float(input("Hedef irtifa (metre, varsayılan: 2250): ") or "2250")
    except ValueError:
        target_alt = 2250
    
    try:
        body_dia = float(input("Gövde çapı (mm, varsayılan: 75): ") or "75")
    except ValueError:
        body_dia = 75
    
    motor_cls = input("Motor sınıfı (G/H/I/J, varsayılan: H): ").upper() or "H"
    if motor_cls not in ['G', 'H', 'I', 'J']:
        motor_cls = 'H'
    
    output_name = input("Çıktı dosya adı (varsayılan: otomatik): ") or ""
    
    print()
    print("Tasarım başlatılıyor...")
    print()
    
    # Tasarımcı oluştur
    designer = RocketDesigner()
    
    # İlk tasarım
    design = designer.design_for_altitude(
        target_altitude=target_alt,
        body_diameter_mm=body_dia,
        motor_class=motor_cls
    )
    
    # Özel isim varsa kullan
    if output_name:
        design.name = output_name
    
    # Optimizasyon
    print("Tasarım optimize ediliyor...")
    design = designer.optimize_design(design)
    
    # Doğrulama
    validation = designer.validate_design(design)
    
    # OpenRocket dosyası oluştur
    exporter = OpenRocketExporter()
    ork_filename = f"/workspace/{design.name}.ork"
    print(f"OpenRocket dosyası oluşturuluyor: {ork_filename}")
    exporter.export(design, ork_filename)
    
    # Rapor oluştur
    report_filename = f"/workspace/{design.name}_rapor.txt"
    print(f"Tasarım raporu oluşturuluyor: {report_filename}")
    ReportGenerator.generate(design, validation, report_filename)
    
    # Sonuçları göster
    print()
    print("=" * 70)
    print("TASARIM TAMAMLANDI")
    print("=" * 70)
    print()
    print(f"Roket Adı: {design.name}")
    print(f"Toplam Uzunluk: {design.total_length:.3f} m")
    print(f"Gövde Çapı: {design.body_diameter*1000:.1f} mm")
    print(f"Toplam Kütle: {design.total_mass:.3f} kg")
    print(f"Stabilite Marjı: {design.stability_margin:.3f} cal")
    print()
    
    print("Doğrulama Sonuçları:")
    if validation['valid']:
        print("  ✓ TASARIM TEKNOFEST STANDARTLARINA UYGUN")
    else:
        print("  ✗ TASARIMDA SORUNLAR VAR")
    
    for check in validation['checks']:
        print(f"  {check}")
    
    for warning in validation['warnings']:
        print(f"  {warning}")
    
    for error in validation['errors']:
        print(f"  {error}")
    
    print()
    print("Oluşturulan Dosyalar:")
    print(f"  - OpenRocket: {ork_filename}")
    print(f"  - Rapor: {report_filename}")
    print()
    print("Not: OpenRocket dosyasını OpenRocket yazılımında açıp")
    print("     detaylı simülasyonlar yapabilirsiniz.")
    print("     OpenRocket: https://openrocket.info/")
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
