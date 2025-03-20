WEB_MERCATOR_SRS = "+init=epsg:3857"

all: world-test.xml world-test-2.xml world-test-cities-limited.xml

clean:
	rm *.xml

%.xml: %.xml.tmpl
	sed -e 's,{{ web_mercator_srs }},'$(WEB_MERCATOR_SRS)',g' $^ > $@
