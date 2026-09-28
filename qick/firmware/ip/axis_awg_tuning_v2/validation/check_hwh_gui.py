"""Check generated HWH parameters/routing and exercise the real offline GUI."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--hwh', type=Path, required=True)
    parser.add_argument('--gui', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    firmware = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(args.gui / 'DCWaveformGeneratorGUI'))
    from qick.sim import QickSim  # desktop PYNQ stubs, no live board
    from qick.awg_tuning import AxisAwgTuningV2
    from PyQt5 import QtCore, QtGui, QtWidgets
    from qick_front_panel import identify_qick_front_panel
    from DCWaveform_Generator import MainWindow

    spec = importlib.util.spec_from_file_location('publish_awg_v2',
        firmware / 'projects/qstl_awg_v2/publish_build.py')
    publisher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(publisher)
    hardware = publisher.validate_hwh(args.hwh.read_bytes())
    root = ET.parse(args.hwh).getroot()
    modules = {m.get('INSTANCE'): m for m in root.iter('MODULE')}
    slaves = {}
    for module in modules.values():
        for bus in module.findall('BUSINTERFACES/BUSINTERFACE'):
            if bus.get('TYPE') in ('SLAVE', 'TARGET'):
                slaves.setdefault(bus.get('BUSNAME'), []).append((module, bus))
    # Retain the known tProcessor ordering, but verify each DAC route in HWH.
    cfg = json.loads((firmware / 'projects/qstl_gui_rtl_sim/soccfg.json').read_text())
    cfg['fw_timestamp'] = 'AWG v2 offline HWH validation'
    checks = []
    for index, gen in enumerate(cfg['gens']):
        if gen['type'] != 'axis_awg_tuning_v1':
            continue
        name = gen['fullpath'].replace('axis_awg_tuning_v1', 'axis_awg_tuning_v2')
        module = modules[name]
        params = {p.get('NAME'): p.get('VALUE') for p in module.findall('PARAMETERS/PARAMETER')}
        driver = AxisAwgTuningV2(dict(type='QICK:QICK:axis_awg_tuning_v2:1.0',
                                    fullpath=name, parameters=params))
        assert driver['step_width'] == 32 and driver['frac'] == 18
        assert driver['ramp_startup_latency_cycles'] == 7
        route = [name]
        bus = module.find("BUSINTERFACES/BUSINTERFACE[@NAME='m_axis']")
        while True:
            destinations = slaves[bus.get('BUSNAME')]
            assert len(destinations) == 1, destinations
            destination, target_bus = destinations[0]
            route.append(destination.get('INSTANCE'))
            if destination.get('MODTYPE') == 'usp_rf_data_converter':
                assert target_bus.get('NAME') == f"s{gen['dac']}_axis"
                break
            assert destination.get('MODTYPE') in ('axis_register_slice', 'axis_register_slice_nb'), (route, destination.get('MODTYPE'))
            bus = destination.find("BUSINTERFACES/BUSINTERFACE[@NAME='M_AXIS']")
            if bus is None:
                bus = destination.find("BUSINTERFACES/BUSINTERFACE[@NAME='m_axis']")
            assert bus is not None
        gen.update(type='axis_awg_tuning_v2', fullpath=name, frac=18, step_width=32)
        checks.append(dict(gen_ch=index, dac=gen['dac'], route=route,
                           width=driver['step_width'], frac=driver['frac']))
    assert len(checks) == 7
    configuration = identify_qick_front_panel(cfg)
    assert set(configuration.awg_tuning_channels) == {c['gen_ch'] for c in checks}
    assert configuration.square_pulse_channels == (7,)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    # The Windows offscreen plugin does not discover installed fonts itself.
    font_path = Path('C:/Windows/Fonts/segoeui.ttf')
    if font_path.exists():
        QtGui.QFontDatabase.addApplicationFont(str(font_path))
        app.setFont(QtGui.QFont('Segoe UI', 9))
    window = MainWindow()
    window._on_qick_configuration_identified(configuration)
    window._multi_ctrl.apply_front_panel_settings({'output_ch': 3})
    window._stability_panel.x_axis.apply_front_panel_settings({'output_ch': 1})
    window._stability_panel.y_axis.apply_front_panel_settings({'output_ch': 3})
    settings = window._stability_run_arguments(save=False)
    channels = dict(zip(settings['sequence'].output_names, settings['awg_channels']))
    assert channels[settings['stability_config'].x_axis.output_name] == 1
    assert channels[settings['stability_config'].y_axis.output_name] == 3
    window._qick_front_panel.setWindowTitle('AWG v2: offline HWH validation (no live board)')
    window._qick_front_panel.set_configuration(configuration)
    window._qick_front_panel.canvas.select_port('output', 5)
    window._qick_front_panel.show()
    app.processEvents()
    window._qick_front_panel.grab().save(str(args.out / 'gui_v2_front_panel.png'))
    result = dict(status='passed', source_hwh=str(args.hwh), live_board=False,
                  hardware=hardware, awg_routes=checks,
                  gui_awg_channels=configuration.awg_tuning_channels,
                  square_channels=configuration.square_pulse_channels,
                  stability_x_gen=1, stability_y_gen=3)
    (args.out / 'hwh_gui_validation.json').write_text(json.dumps(result, indent=2))
    window._qick_front_panel.close()
    window.close()
    window.deleteLater()
    app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
    app.processEvents()
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
