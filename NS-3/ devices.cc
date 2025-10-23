#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/lorawan-module.h"
#include "ns3/mobility-module.h"
#include "ns3/applications-module.h"
#include "ns3/internet-module.h"
#include "ns3/log.h"
#include "ns3/propagation-loss-model.h"
#include "ns3/propagation-delay-model.h"

using namespace ns3;
using namespace lorawan;

NS_LOG_COMPONENT_DEFINE ("LoraThreeDevices");

int main (int argc, char *argv[])
{
  // Параметры по умолчанию
  int nDevices = 3;
  double simulationTime = 3600;
  double appPeriod = 600;
  double noiseFigure = 7.0; // Коэффициент шума в dB
  double frequency = 868e6; // Частота 868 MHz

  // Настройка логирования
  LogComponentEnable ("LoraThreeDevices", LOG_LEVEL_INFO);
  LogComponentEnable ("LoraPacketTracker", LOG_LEVEL_INFO);

  NS_LOG_INFO("Создаем сеть LoRaWAN с " << nDevices << " устройствами");

  // Создание узлов 
  NodeContainer endDevices;
  endDevices.Create (nDevices);
  NodeContainer gateways;
  gateways.Create (1);

  // Настройка реального беспроводного канала
  
  // Создание модели потерь с учётом затуханий 
  Ptr<LogDistancePropagationLossModel> logDistanceLossModel = CreateObject<LogDistancePropagationLossModel>();
  logDistanceLossModel->SetAttribute("Exponent", DoubleValue(3.0)); // Показатель затухания (3.0 для городской среды)
  logDistanceLossModel->SetAttribute("ReferenceLoss", DoubleValue(46.6777)); // Потери на 1м для 868MHz
  
  // Случайные потери (замирания)
  Ptr<RandomPropagationLossModel> randomLossModel = CreateObject<RandomPropagationLossModel>();
  randomLossModel->SetAttribute("Variable", DoubleValue(5.0)); // Случайные колебания ±5dB
  logDistanceLossModel->SetNext(randomLossModel);
  
  // Модель задержки сигнала
  Ptr<ConstantSpeedPropagationDelayModel> delayModel = CreateObject<ConstantSpeedPropagationDelayModel>();

  // Канал с этими моделями
  Ptr<WirelessChannel> wirelessChannel = CreateObject<WirelessChannel>();
  wirelessChannel->SetAttribute("PropagationLossModel", PointerValue(logDistanceLossModel));
  wirelessChannel->SetAttribute("PropagationDelayModel", PointerValue(delayModel));

  // Настройка мобильности (размещение и передвижение узлов)
  MobilityHelper mobility;
  
  // Шлюз в центре
  Ptr<ListPositionAllocator> positionAllocGateways = CreateObject<ListPositionAllocator> ();
  positionAllocGateways->Add (Vector (0.0, 0.0, 15.0));
  mobility.SetPositionAllocator (positionAllocGateways);
  mobility.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
  mobility.Install (gateways);

  // Устройства распределяем случайно в радиусе 2км
  MobilityHelper mobilityEd;
  mobilityEd.SetPositionAllocator ("ns3::UniformDiscPositionAllocator",
                                  "X", DoubleValue (0.0),
                                  "Y", DoubleValue (0.0),
                                  "rho", DoubleValue (2000.0));
  mobilityEd.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
  mobilityEd.Install (endDevices);

  
  // Настройка PHY с учетом шума
  
  // Создание помощника для PHY с каналом
  PhyLoraPropModelHelper phyHelper;
  phyHelper.SetChannel(wirelessChannel);
  phyHelper.SetFrequency(frequency);
  phyHelper.SetAttribute("NoiseFigure", DoubleValue(noiseFigure)); // Добавляем коэффициент шума
  phyHelper.SetAttribute("TxPower", DoubleValue(14)); // Мощность передачи по умолчанию
  
  // Альтернативный вариант: использование более продвинутой модели канала
  // Лучше использовать для большего количества устройств
  // Ptr<ThreeLogDistancePropagationLossModel> lossModel = CreateObject<ThreeLogDistancePropagationLossModel>();
  // lossModel->SetAttribute("Exponent0", DoubleValue(1.0));  // Ближняя зона
  // lossModel->SetAttribute("Exponent1", DoubleValue(2.0));  // Средняя зона  
  // lossModel->SetAttribute("Exponent2", DoubleValue(3.5));  // Дальняя зона

  // LoRa MAC уровень
  LorawanMacHelper macHelper;
  macHelper.SetRegion(LorawanMacHelper::EU);

  // LoRaWAN helper
  LorawanHelper helper;
  helper.EnablePacketTracking();

  // Установка LoRa на устройства
  macHelper.SetDeviceType(LorawanMacHelper::ED_A);
  helper.Install(phyHelper, macHelper, endDevices);

  // Настройка для шлюза
  macHelper.SetDeviceType(LorawanMacHelper::GW);
  helper.Install(phyHelper, macHelper, gateways);

  // Настройка индивидуальных параметров устройств
  for (int i = 0; i < nDevices; i++) {
    Ptr<Node> node = endDevices.Get(i);
    Ptr<LoraNetDevice> loraNetDev = node->GetDevice(0)->GetObject<LoraNetDevice>();
    Ptr<ClassAEndDeviceLorawanMac> edMac = loraNetDev->GetMac()->GetObject<ClassAEndDeviceLorawanMac>();
    
    // Устанавливаем разные параметры для каждого устройства
    switch(i) {
      case 0: // Близко к шлюзу
        edMac->SetDataRate(5);  // SF7
        edMac->SetTransmissionPower(14);
        NS_LOG_INFO("Устройство 0: SF7, мощность 14dBm");
        break;
      case 1: // Среднее расстояние
        edMac->SetDataRate(3);  // SF9
        edMac->SetTransmissionPower(10);
        NS_LOG_INFO("Устройство 1: SF9, мощность 10dBm");
        break;
      case 2: // Далеко от шлюза
        edMac->SetDataRate(1);  // SF11
        edMac->SetTransmissionPower(6);
        NS_LOG_INFO("Устройство 2: SF11, мощность 6dBm");
        break;
    }
  }

  // Создание приложения
  Time appStopTime = Seconds (simulationTime);
  PeriodicSenderHelper appHelper = PeriodicSenderHelper ();
  appHelper.SetPeriod (Seconds (appPeriod));
  
  Ptr<RandomVariableStream> rv = CreateObjectWithAttributes<UniformRandomVariable> (
    "Min", DoubleValue (10), "Max", DoubleValue (50));
  appHelper.SetPacketSizeRandomVariable (rv);

  ApplicationContainer appContainer = appHelper.Install (endDevices);
  appContainer.Start (Seconds (0));
  appContainer.Stop (appStopTime);

  // Подключение шлюза к серверу
  NetworkServerHelper networkServerHelper;
  networkServerHelper.SetGateways (gateways);
  networkServerHelper.SetEndDevices (endDevices);
  networkServerHelper.Install (gateways);

  ApplicationContainer serverContainer;
  ForwarderHelper forwarderHelper;
  forwarderHelper.Install (gateways);

  // Дополнительная информация о канале
  NS_LOG_INFO("Настройки беспроводного канала:");
  NS_LOG_INFO("- Коэффициент шума: " << noiseFigure << " dB");
  NS_LOG_INFO("- Частота: " << frequency/1e6 << " MHz");
  NS_LOG_INFO("- Показатель затухания: 3.0 (городская среда)");

  // Запуск симуляции
  NS_LOG_INFO("Запускаем симуляцию на " << simulationTime << " секунд");
  Simulator::Stop (appStopTime + Hours (1));
  Simulator::Run ();
  Simulator::Destroy ();

  // Вывод результатов
  LoraPacketTracker& tracker = helper.GetPacketTracker();
  NS_LOG_INFO("--- РЕЗУЛЬТАТЫ СИМУЛЯЦИИ ---");
  NS_LOG_INFO("Всего отправлено пакетов: " << tracker.CountMacPacketsSent());
  NS_LOG_INFO("Успешно доставлено: " << tracker.CountMacPacketsGloballyReceived());
  
  for (int i = 0; i < nDevices; i++) {
    Ptr<Node> node = endDevices.Get(i);
    Vector pos = node->GetObject<MobilityModel>()->GetPosition();
    NS_LOG_INFO("Устройство " << i << " позиция: (" << pos.x << ", " << pos.y << ")");
  }

  return 0;
}
