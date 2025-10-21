#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/lorawan-module.h"
#include "ns3/mobility-module.h"
#include "ns3/applications-module.h"
#include "ns3/internet-module.h"
#include "ns3/log.h"

using namespace ns3;
using namespace lorawan;

NS_LOG_COMPONENT_DEFINE ("LoraThreeDevices");

int main (int argc, char *argv[])
{
  // Параметры по умолчанию
  int nDevices = 3;           // Количество устройств
  double simulationTime = 3600; // Время симуляции в секундах (1 час)
  double appPeriod = 600;     // Период отправки данных (10 минут)

  // Настройка логирования
  LogComponentEnable ("LoraThreeDevices", LOG_LEVEL_INFO);
  LogComponentEnable ("LoraPacketTracker", LOG_LEVEL_INFO);

  NS_LOG_INFO("Создаем сеть LoRaWAN с " << nDevices << " устройствами");

  // Создание узлов 
  NodeContainer endDevices;
  endDevices.Create (nDevices);

  NodeContainer gateways;
  gateways.Create (1);  // Один шлюз

  // Настройка мобильности
  MobilityHelper mobility;
  
  // Шлюз в центре
  Ptr<ListPositionAllocator> positionAllocGateways = CreateObject<ListPositionAllocator> ();
  positionAllocGateways->Add (Vector (0.0, 0.0, 15.0)); // Высота 15м
  mobility.SetPositionAllocator (positionAllocGateways);
  mobility.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
  mobility.Install (gateways);

  // Устройства распределяем случайно в радиусе 2км
  MobilityHelper mobilityEd;
  mobilityEd.SetPositionAllocator ("ns3::UniformDiscPositionAllocator",
                                  "X", DoubleValue (0.0),
                                  "Y", DoubleValue (0.0),
                                  "rho", DoubleValue (2000.0)); // Радиус 2000м
  mobilityEd.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
  mobilityEd.Install (endDevices);

  //Создание LORAWAN стека
  // LoRa физический уровень
  PhyLoraPropModelHelper phyHelper;
  phyHelper.SetFrequency(868e6); // EU 868 MHz

  // LoRa MAC уровень
  LorawanMacHelper macHelper;
  macHelper.SetRegion(LorawanMacHelper::EU); // Европейский регион

  // LoRaWAN helper
  LorawanHelper helper;
  helper.EnablePacketTracking(); // Включаем отслеживание пакетов

  // Установка LoRa на устройства
  // Настройка для конечных устройств
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
      case 0: // Устройство 1 - близко к шлюзу
        edMac->SetDataRate(5);  // SF7
        edMac->SetTransmissionPower(14); // dBm
        NS_LOG_INFO("Устройство 0: SF7, мощность 14dBm");
        break;
      case 1: // Устройство 2 - среднее расстояние
        edMac->SetDataRate(3);  // SF9
        edMac->SetTransmissionPower(10); // dBm
        NS_LOG_INFO("Устройство 1: SF9, мощность 10dBm");
        break;
      case 2: // Устройство 3 - далеко от шлюза
        edMac->SetDataRate(1);  // SF11
        edMac->SetTransmissionPower(6);  // dBm
        NS_LOG_INFO("Устройство 2: SF11, мощность 6dBm");
        break;
    }
  }

  // Создание приложения
  Time appStopTime = Seconds (simulationTime);
  PeriodicSenderHelper appHelper = PeriodicSenderHelper ();
  appHelper.SetPeriod (Seconds (appPeriod));
  
  // Устанавливаем разные размеры пакетов для разных устройств
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

  // Установка сетевых приложений
  ApplicationContainer serverContainer;
  ForwarderHelper forwarderHelper;
  forwarderHelper.Install (gateways);

  // Запуск симмуляции
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
    Vector pos = node->GetObject<MobilityModel>()->GetPosition();// Простейшая сеть на 2 узла в ns-3
#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/applications-module.h"

using namespace ns3;

int main(int argc, char *argv[])
{
  // Включение логирования
  Time::SetResolution(Time::NS);
  LogComponentEnable("UdpEchoClientApplication", LOG_LEVEL_INFO);
  LogComponentEnable("UdpEchoServerApplication", LOG_LEVEL_INFO);

  std::cout << "Создаем сеть из 2 узлов..." << std::endl;

  // Создание узла 2
  NodeContainer nodes;
  nodes.Create(2);

  // Создание каналов связи
  PointToPointHelper pointToPoint;
  pointToPoint.SetDeviceAttribute("DataRate", StringValue("5Mbps"));
  pointToPoint.SetChannelAttribute("Delay", StringValue("2ms"));

  // Уставновка сестевых интерфейсов
  NetDeviceContainer devices;
  devices = pointToPoint.Install(nodes);

  // Установка стека протоколов TCP/IP
  InternetStackHelper stack;
  stack.Install(nodes);

  // Назначение IP-адрессов
  Ipv4AddressHelper address;
  address.SetBase("10.1.1.0", "255.255.255.0");
  Ipv4InterfaceContainer interfaces = address.Assign(devices);

  // Создание сервера во втором узле
  UdpEchoServerHelper echoServer(9); // Порт 9
  ApplicationContainer serverApps = echoServer.Install(nodes.Get(1));
  serverApps.Start(Seconds(1.0));
  serverApps.Stop(Seconds(10.0));

  // Создание клиента в первом узле
  UdpEchoClientHelper echoClient(interfaces.GetAddress(1), 9);
  echoClient.SetAttribute("MaxPackets", UintegerValue(3));
  echoClient.SetAttribute("Interval", TimeValue(Seconds(1.0)));
  echoClient.SetAttribute("PacketSize", UintegerValue(512));

  ApplicationContainer clientApps = echoClient.Install(nodes.Get(0));
  clientApps.Start(Seconds(2.0));
  clientApps.Stop(Seconds(6.0));

  std::cout << "Дительность симмуляции 10 секунд" << std::endl;

  // Запуск симмуляции
  Simulator::Run();
  Simulator::Destroy();

  std::cout << "Симуляция завершена!" << std::endl;
  return 0;
}
    NS_LOG_INFO("Устройство " << i << " позиция: (" << pos.x << ", " << pos.y << ")");
  }

  return 0;
}
