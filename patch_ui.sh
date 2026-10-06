# Patch XRP frontend
cd /root/bot_xrp/web_app/frontend/dist/assets
js_file=$(ls index-*.js)
sed -i 's/DOGEUSDT/XRPUSDT/g' $js_file
sed -i 's/DOGE/XRP/g' $js_file
sed -i 's/3m (DEGEN MODE)/5m/g' $js_file
sed -i 's/XRP_3M_DEGEN/XRP_PURE_ROBUST/g' $js_file

# Patch SOL frontend
cd /root/bot_sol/web_app/frontend/dist/assets
js_file=$(ls index-*.js)
sed -i 's/DOGEUSDT/SOLUSDT/g' $js_file
sed -i 's/DOGE/SOL/g' $js_file
sed -i 's/3m (DEGEN MODE)/4h/g' $js_file
sed -i 's/SOL_3M_DEGEN/SOL_GOD_MODE/g' $js_file
