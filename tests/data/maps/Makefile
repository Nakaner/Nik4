WEB_MERCATOR_SRS = "epsg:3857"

all: world-test.xml world-test-2.xml world-test-cities-limited.xml land-cities-rivers.xml land-cities-rivers-1disabled.xml

clean:
	rm *.xml

%.xml: %.xml.tmpl
	sed -e 's,{{ web_mercator_srs }},'$(WEB_MERCATOR_SRS)',g' $^ > $@
