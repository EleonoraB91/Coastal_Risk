<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<!--
  cvi_style.qml
  Stile QGIS per la visualizzazione del Coastal Vulnerability Index.
  5 classi di rischio con palette verde→rosso.
  Da assegnare al layer linea di riva dopo il calcolo CVI.
-->
<qgis version="3.16" styleCategories="AllStyleCategories">
  <renderer-v2 type="graduatedSymbol" attr="CVI" graduatedMethod="GraduatedColor">
    <ranges>
      <range lower="1.0"  upper="1.5"  label="Molto Basso" symbol="0" render="true"/>
      <range lower="1.5"  upper="2.5"  label="Basso"        symbol="1" render="true"/>
      <range lower="2.5"  upper="3.5"  label="Medio"        symbol="2" render="true"/>
      <range lower="3.5"  upper="4.5"  label="Alto"         symbol="3" render="true"/>
      <range lower="4.5"  upper="5.0"  label="Molto Alto"   symbol="4" render="true"/>
    </ranges>
    <!-- I simboli concreti vengono generati dal StyleManager in Fase 3 -->
  </renderer-v2>
</qgis>
